"""
Taskiq-задачи оркестрации пайплайна генерации ТЗ.

Сценарии:
  1. full_pipeline_task        — первичная генерация (создание чата)
  2. update_tz_task            — обновление ТЗ (новые файлы + комментарий)
  3. regenerate_block_task     — точечная перегенерация блока
  4. generate_custom_block_task — генерация/заполнение кастомного блока
"""

from __future__ import annotations

import json
from typing import Any

import structlog
import redis.asyncio as aredis
from dishka.integrations.taskiq import FromDishka, inject

from backend.app.domain.chat.value_objects.types import EventType, GenerationRunStatus
from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.infrastructure.persistent.generation import GenerationRepository
from backend.app.infrastructure.storage import StorageWorker
from backend.app.infrastructure.utils.channels import get_channel_name
from backend.worker.broker import broker
from backend.worker.modules.machine_learning.interface import (
    DataSource,
    ProgressNotifier,
)
from backend.worker.modules.machine_learning.mock_adapter import MockITZPipelineAdapter
from backend.worker.modules.machine_learning.schemas.enums import TemplateType
from backend.worker.modules.machine_learning.templates import get_template_class
from backend.worker.modules.export.renderer import TemplateMarkdownRenderer
from backend.worker.modules.export.exporters import get_exporter

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_notifier_callback(
    chat_id: int,
    run_id: int,
    channel_name: str,
    gen_repo: GenerationRepository,
    redis_client: aredis.Redis,
) -> ProgressNotifier:
    """Фабрика notifier-коллбэка: пишет статус в БД и публикует в Redis."""

    async def _callback(event_name: str, payload: dict[str, Any]) -> None:
        step_message = payload.get("message", "")
        progress = payload.get("progress", 0)

        await gen_repo.update_status(
            run_id=run_id,
            status=event_name,
            step=step_message,
            progress=progress,
        )

        await redis_client.publish(
            channel_name,
            json.dumps({
                "type": EventType.GENERATION_STATUS,
                "chat_id": chat_id,
                "status": event_name,
                "step": step_message,
                "progress": progress,
            }),
        )

    return _callback


def _load_adapter(state_json: str | None) -> MockITZPipelineAdapter:
    """Восстанавливает адаптер из JSON-стейта.

    Возвращает ``MockITZPipelineAdapter``; при подключении боевого адаптера
    достаточно заменить этот вызов (или вынести фабрику в DI).
    """
    if state_json is None:
        return MockITZPipelineAdapter()
    return MockITZPipelineAdapter.load_state(json.loads(state_json))


async def _persist_result(
    *,
    adapter: MockITZPipelineAdapter,
    result: Any,
    chat_id: int,
    run_id: int,
    channel_name: str,
    gen_repo: GenerationRepository,
    chat_repo: ChatRepository,
    storage: StorageWorker,
    redis_client: aredis.Redis,
    config: AppSettings,
) -> None:
    """Сохраняет стейт адаптера, результат ТЗ в S3/БД и публикует финальное WS-уведомление."""

    # Стейт адаптера
    await gen_repo.save_state(run_id, json.dumps(adapter.save_state()))

    # Результат в S3
    result_json = result.model_dump_json()
    result_key = f"tz-results/{chat_id}/{run_id}.json"

    await storage.put_object(
        bucket=config.storage.BUCKET_NAME,
        key=result_key,
        data=result_json.encode("utf-8"),
        content_type="application/json",
    )

    await gen_repo.save_result(run_id, result_key)

    # Markdown-сообщение в чат
    markdown_text = (
        result.document.to_markdown()
        if hasattr(result.document, "to_markdown")
        else result_json
    )

    msg = await chat_repo.create_message_async(
        chat_id=chat_id,
        text=markdown_text,
        is_user_sender=False,
    )

    await redis_client.publish(
        channel_name,
        json.dumps({
            "id": msg.id,
            "chat_id": chat_id,
            "text": markdown_text,
            "type": EventType.LLM_ANSWER,
            "created_at": msg.created_at.isoformat(),
        }),
    )


async def _fail_run(
    *,
    run_id: int,
    chat_id: int,
    channel_name: str,
    gen_repo: GenerationRepository,
    redis_client: aredis.Redis,
    error_text: str = "Internal pipeline error",
) -> None:
    """Помечает run как FAILED и уведомляет фронтенд."""
    await gen_repo.mark_failed(run_id, error_text)
    await redis_client.publish(
        channel_name,
        json.dumps({
            "type": EventType.ERROR,
            "chat_id": chat_id,
        }),
    )


# ---------------------------------------------------------------------------
# 1. Полный пайплайн первичной генерации
# ---------------------------------------------------------------------------

@broker.task(task_name="full_pipeline")
@inject
async def full_pipeline_task(
    chat_id: int,
    user_id: int,
    parsed_files: list[dict[str, str]],
    chat_repo: FromDishka[ChatRepository],
    gen_repo: FromDishka[GenerationRepository],
    redis_client: FromDishka[aredis.Redis],
    storage: FromDishka[StorageWorker],
    config: FromDishka[AppSettings],
) -> None:
    """
    Первичная генерация ТЗ после создания чата и загрузки файлов.

    ``parsed_files`` — список словарей ``{"id": ..., "type": ..., "content": ...}``,
    уже распарсенных на предыдущем шаге (parse_file_task).
    """
    channel_name = get_channel_name(user_id)
    log = logger.bind(chat_id=chat_id, user_id=user_id)

    run = await gen_repo.create_run(chat_id=chat_id, user_id=user_id)
    log = log.bind(run_id=run.id)

    try:
        log.info("full_pipeline_started")

        # Шаг 1: Инициализация пустого адаптера
        adapter = MockITZPipelineAdapter()
        notifier = get_notifier_callback(chat_id, run.id, channel_name, gen_repo, redis_client)
        adapter.attach_notifier(notifier)

        # Шаг 2: Ingest sources
        await gen_repo.update_status(
            run.id, GenerationRunStatus.INGESTING, step="Обработка источников", progress=0,
        )
        sources = [DataSource(**pf) for pf in parsed_files]
        conflicts = await adapter.ingest_sources(sources)
        log.info("ingest_completed", conflicts_count=len(conflicts))

        # Шаг 3: Compile document
        await gen_repo.update_status(
            run.id, GenerationRunStatus.COMPILING, step="Сборка итогового ТЗ", progress=0,
        )
        result = await adapter.compile_document()

        # Шаг 4: Persist
        await _persist_result(
            adapter=adapter,
            result=result,
            chat_id=chat_id,
            run_id=run.id,
            channel_name=channel_name,
            gen_repo=gen_repo,
            chat_repo=chat_repo,
            storage=storage,
            redis_client=redis_client,
            config=config,
        )

        log.info("full_pipeline_completed", result_key=f"tz-results/{chat_id}/{run.id}.json")

    except Exception:
        log.exception("full_pipeline_failed")
        await _fail_run(
            run_id=run.id,
            chat_id=chat_id,
            channel_name=channel_name,
            gen_repo=gen_repo,
            redis_client=redis_client,
        )


# ---------------------------------------------------------------------------
# 2. Обновление ТЗ (новые файлы + глобальный комментарий)
# ---------------------------------------------------------------------------

@broker.task(task_name="update_tz")
@inject
async def update_tz_task(
    chat_id: int,
    user_id: int,
    new_parsed_files: list[dict[str, str]] | None = None,
    comment: str | None = None,
    chat_repo: FromDishka[ChatRepository] = None,  # type: ignore[assignment]
    gen_repo: FromDishka[GenerationRepository] = None,  # type: ignore[assignment]
    redis_client: FromDishka[aredis.Redis] = None,  # type: ignore[assignment]
    storage: FromDishka[StorageWorker] = None,  # type: ignore[assignment]
    config: FromDishka[AppSettings] = None,  # type: ignore[assignment]
) -> None:
    """
    Обновление уже существующего ТЗ: догрузка файлов и/или глобальный комментарий.
    """
    channel_name = get_channel_name(user_id)
    log = logger.bind(chat_id=chat_id, user_id=user_id)

    # Загружаем последний успешный run для восстановления стейта
    latest_run = await gen_repo.get_latest_run(chat_id)
    state_json: str | None = getattr(latest_run, "state_json", None) if latest_run else None

    run = await gen_repo.create_run(chat_id=chat_id, user_id=user_id)
    log = log.bind(run_id=run.id)

    try:
        log.info("update_tz_started")

        # Шаг 1: Восстановление адаптера
        adapter = _load_adapter(state_json)
        notifier = get_notifier_callback(chat_id, run.id, channel_name, gen_repo, redis_client)
        adapter.attach_notifier(notifier)

        result = None

        # Шаг 2: Ingest новых файлов (если есть)
        if new_parsed_files:
            await gen_repo.update_status(
                run.id, GenerationRunStatus.INGESTING, step="Обработка новых источников", progress=0,
            )
            sources = [DataSource(**pf) for pf in new_parsed_files]
            conflicts = await adapter.ingest_sources(sources)
            log.info("ingest_new_files_completed", conflicts_count=len(conflicts))

        # Шаг 3: Применение глобального комментария (если есть)
        if comment:
            await gen_repo.update_status(
                run.id, GenerationRunStatus.COMPILING, step="Применяем комментарий", progress=0,
            )
            result = await adapter.apply_global_comment(comment)

        # Шаг 4: Пересборка ТЗ (если комментарий не вернул результат)
        if result is None:
            await gen_repo.update_status(
                run.id, GenerationRunStatus.COMPILING, step="Пересборка ТЗ", progress=0,
            )
            result = await adapter.compile_document()

        # Шаг 5: Persist
        await _persist_result(
            adapter=adapter,
            result=result,
            chat_id=chat_id,
            run_id=run.id,
            channel_name=channel_name,
            gen_repo=gen_repo,
            chat_repo=chat_repo,
            storage=storage,
            redis_client=redis_client,
            config=config,
        )

        log.info("update_tz_completed")

    except Exception:
        log.exception("update_tz_failed")
        await _fail_run(
            run_id=run.id,
            chat_id=chat_id,
            channel_name=channel_name,
            gen_repo=gen_repo,
            redis_client=redis_client,
        )


# ---------------------------------------------------------------------------
# 3. Точечная перегенерация блока
# ---------------------------------------------------------------------------

@broker.task(task_name="regenerate_block")
@inject
async def regenerate_block_task(
    chat_id: int,
    user_id: int,
    field_path: str,
    instruction: str | None = None,
    chat_repo: FromDishka[ChatRepository] = None,  # type: ignore[assignment]
    gen_repo: FromDishka[GenerationRepository] = None,  # type: ignore[assignment]
    redis_client: FromDishka[aredis.Redis] = None,  # type: ignore[assignment]
    storage: FromDishka[StorageWorker] = None,  # type: ignore[assignment]
    config: FromDishka[AppSettings] = None,  # type: ignore[assignment]
) -> None:
    """
    Перегенерация конкретного блока ТЗ по ``field_path``.
    """
    channel_name = get_channel_name(user_id)
    log = logger.bind(chat_id=chat_id, user_id=user_id, field_path=field_path)

    latest_run = await gen_repo.get_latest_run(chat_id)
    state_json: str | None = getattr(latest_run, "state_json", None) if latest_run else None

    run = await gen_repo.create_run(chat_id=chat_id, user_id=user_id)
    log = log.bind(run_id=run.id)

    try:
        log.info("regenerate_block_started")

        adapter = _load_adapter(state_json)
        notifier = get_notifier_callback(chat_id, run.id, channel_name, gen_repo, redis_client)
        adapter.attach_notifier(notifier)

        await gen_repo.update_status(
            run.id, GenerationRunStatus.COMPILING,
            step=f"Перегенерация блока «{field_path}»", progress=0,
        )

        result = await adapter.regenerate_block(field_path, instruction)

        await _persist_result(
            adapter=adapter,
            result=result,
            chat_id=chat_id,
            run_id=run.id,
            channel_name=channel_name,
            gen_repo=gen_repo,
            chat_repo=chat_repo,
            storage=storage,
            redis_client=redis_client,
            config=config,
        )

        log.info("regenerate_block_completed")

    except Exception:
        log.exception("regenerate_block_failed")
        await _fail_run(
            run_id=run.id,
            chat_id=chat_id,
            channel_name=channel_name,
            gen_repo=gen_repo,
            redis_client=redis_client,
        )


# ---------------------------------------------------------------------------
# 4. Генерация/заполнение кастомного или пустого блока
# ---------------------------------------------------------------------------

@broker.task(task_name="generate_custom_block")
@inject
async def generate_custom_block_task(
    chat_id: int,
    user_id: int,
    field_path: str,
    custom_topic: str,
    chat_repo: FromDishka[ChatRepository] = None,  # type: ignore[assignment]
    gen_repo: FromDishka[GenerationRepository] = None,  # type: ignore[assignment]
    redis_client: FromDishka[aredis.Redis] = None,  # type: ignore[assignment]
    storage: FromDishka[StorageWorker] = None,  # type: ignore[assignment]
    config: FromDishka[AppSettings] = None,  # type: ignore[assignment]
) -> None:
    """
    Генерация контента для кастомного блока, добавленного через UI,
    или заполнение пустого обязательного блока.
    """
    channel_name = get_channel_name(user_id)
    log = logger.bind(chat_id=chat_id, user_id=user_id, field_path=field_path)

    latest_run = await gen_repo.get_latest_run(chat_id)
    state_json: str | None = getattr(latest_run, "state_json", None) if latest_run else None

    run = await gen_repo.create_run(chat_id=chat_id, user_id=user_id)
    log = log.bind(run_id=run.id)

    try:
        log.info("generate_custom_block_started")

        adapter = _load_adapter(state_json)
        notifier = get_notifier_callback(chat_id, run.id, channel_name, gen_repo, redis_client)
        adapter.attach_notifier(notifier)

        await gen_repo.update_status(
            run.id, GenerationRunStatus.COMPILING,
            step=f"Генерация блока «{custom_topic}»", progress=0,
        )

        result = await adapter.generate_custom_block_content(field_path, custom_topic)

        await _persist_result(
            adapter=adapter,
            result=result,
            chat_id=chat_id,
            run_id=run.id,
            channel_name=channel_name,
            gen_repo=gen_repo,
            chat_repo=chat_repo,
            storage=storage,
            redis_client=redis_client,
            config=config,
        )

        log.info("generate_custom_block_completed")

    except Exception:
        log.exception("generate_custom_block_failed")
        await _fail_run(
            run_id=run.id,
            chat_id=chat_id,
            channel_name=channel_name,
            gen_repo=gen_repo,
            redis_client=redis_client,
        )


# ---------------------------------------------------------------------------
# 5. Экспорт ТЗ
# ---------------------------------------------------------------------------


def _append_custom_sections(
    master_markdown: str,
    custom_sections: dict[str, list[dict[str, Any]]],
) -> str:
    """Добавляет пользовательские подпункты к Master Markdown."""
    lines = [master_markdown.rstrip()]

    for _section_key, nodes in custom_sections.items():
        if not nodes:
            continue
        for node in nodes:
            _render_custom_node(node, level=3, lines=lines)

    return "\n".join(lines)


def _render_custom_node(
    node: dict[str, Any],
    level: int,
    lines: list[str],
) -> None:
    title = node.get("title", "").strip()
    content = node.get("content", "").strip()
    children = node.get("children", [])

    if not title and not content and not children:
        return

    heading = "#" * min(level, 6)
    if title:
        lines.append("")
        lines.append(f"{heading} {title}")
        lines.append("")
    if content:
        lines.append(content)
        lines.append("")
    for child in children:
        _render_custom_node(child, level + 1, lines)


@broker.task(task_name="export_tz")
@inject
async def export_tz_task(
    chat_id: int,
    user_id: int,
    result_key: str,
    export_format: str,
    redis_client: FromDishka[aredis.Redis] = None,  # type: ignore[assignment]
    storage: FromDishka[StorageWorker] = None,  # type: ignore[assignment]
    config: FromDishka[AppSettings] = None,  # type: ignore[assignment]
) -> None:
    """
    Экспорт ТЗ в файл (markdown, word, pdf).

    Алгоритм:
      1. Загружает JSON-результат из S3.
      2. Восстанавливает Pydantic-модель шаблона через ``TEMPLATE_REGISTRY``.
      3. Рендерит «Master Markdown» через ``TemplateMarkdownRenderer``.
      4. Передаёт Markdown в соответствующий ``ITzExporter`` (Strategy).
      5. Загружает готовый файл в S3 и публикует ``EXPORT_READY``.
    """
    channel_name = get_channel_name(user_id)
    log = logger.bind(chat_id=chat_id, user_id=user_id, export_format=export_format)

    try:
        log.info("export_tz_started")

        # 1. Загружаем JSON из S3
        content_text = await storage.get_text(config.storage.BUCKET_NAME, result_key)
        content = json.loads(content_text)

        # 2. Восстанавливаем Pydantic-модель
        template_type_str = content.get("template_type", "")
        document_data = content.get("document", {})
        custom_sections = content.get("custom_sections", {})

        template_type = TemplateType(template_type_str)
        template_class = get_template_class(template_type)

        # 3. Рендерим Master Markdown
        renderer = TemplateMarkdownRenderer()
        try:
            template = template_class.model_validate(document_data)
            master_markdown = renderer.render(template)
        except Exception:
            # После ручного редактирования (manual-edit) поля могут быть
            # заменены на plain-строки — model_validate упадёт.
            # Используем dict-рендерер как fallback.
            log.info("model_validate_failed_using_dict_renderer")
            master_markdown = renderer.render_from_data(document_data, template_class)

        # Добавляем пользовательские подпункты в конец каждого раздела
        if custom_sections:
            master_markdown = _append_custom_sections(master_markdown, custom_sections)

        # 4. Экспортируем через стратегию
        exporter = get_exporter(export_format)
        export_data = await exporter.export(master_markdown)

        # 5. Сохраняем в S3
        base_name = result_key.rsplit("/", 1)[-1].replace(".json", "")
        export_key = f"exports/{chat_id}/{base_name}.{exporter.file_extension}"

        await storage.put_object(
            bucket=config.storage.BUCKET_NAME,
            key=export_key,
            data=export_data,
            content_type=exporter.content_type,
        )

        await redis_client.publish(
            channel_name,
            json.dumps({
                "type": EventType.EXPORT_READY,
                "chat_id": chat_id,
                "export_key": export_key,
                "format": export_format,
            }),
        )

        log.info("export_tz_completed", export_key=export_key)

    except Exception:
        log.exception("export_tz_failed")
        await redis_client.publish(
            channel_name,
            json.dumps({
                "type": EventType.ERROR,
                "chat_id": chat_id,
            }),
        )
