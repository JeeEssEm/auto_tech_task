import asyncio
import json
import re
from datetime import UTC, datetime

import redis.asyncio as aredis
import structlog
from dishka.integrations.taskiq import FromDishka, inject

from backend.app.domain.chat.value_objects.types import EventType, GenerationRunStatus
from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.infrastructure.persistent.generation import GenerationRepository
from backend.app.infrastructure.persistent.llm_pipeline import GKGRepository
from backend.app.infrastructure.storage import StorageWorker
from backend.app.infrastructure.utils.channels import get_channel_name
from backend.worker.broker import broker
from backend.worker.modules.export.exporters import get_exporter
from backend.worker.modules.llm_pipeline.orchestrator.nodes import OrchestratorDeps
from backend.worker.modules.llm_pipeline.orchestrator.state import Attachment

logger = structlog.get_logger(__name__)

_REF_TAG_REGEX = re.compile(r"<ref\b[^>]*\/>")
_CODE_WRAPPED_REF_REGEX = re.compile(r"`\s*<ref\b[^>]*\/>\s*`")
_ATX_HEADING_REGEX = re.compile(r"^(\s{0,3})(#{1,6})(\s+)(.*)$")


def _strip_ref_tags(text: str) -> str:
    cleaned = _CODE_WRAPPED_REF_REGEX.sub("", text)
    cleaned = _REF_TAG_REGEX.sub("", cleaned)
    cleaned = cleaned.replace("``", "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned


def _normalize_content_headings(content_md: str, section_heading_level: int) -> str:
    lines = content_md.splitlines()
    heading_levels: list[int] = []

    for line in lines:
        m = _ATX_HEADING_REGEX.match(line)
        if m:
            heading_levels.append(len(m.group(2)))

    if not heading_levels:
        return content_md

    min_content_level = min(heading_levels)
    required_min_level = min(section_heading_level + 1, 6)
    shift = max(0, required_min_level - min_content_level)
    if shift == 0:
        return content_md

    normalized: list[str] = []
    for line in lines:
        m = _ATX_HEADING_REGEX.match(line)
        if not m:
            normalized.append(line)
            continue

        indent, hashes, sep, rest = m.groups()
        new_level = min(len(hashes) + shift, 6)
        normalized.append(f"{indent}{'#' * new_level}{sep}{rest}")

    return "\n".join(normalized)


def _sanitize_export_content_md(content_md: str, section_heading_level: int) -> str:
    cleaned = _strip_ref_tags(content_md)
    return _normalize_content_headings(cleaned, section_heading_level)


def _render_sections_to_markdown(sections: list[dict]) -> str:
    lines: list[str] = ["# Техническое задание", ""]

    for section in sections:
        title = str(section.get("title") or section.get("section_id") or "Раздел").strip()
        level_raw = int(section.get("level") or 1)
        heading_level = max(2, min(level_raw + 1, 6))
        content_md = str(section.get("content_md") or "").strip()
        content_md = _sanitize_export_content_md(content_md, heading_level)

        lines.append(f"{'#' * heading_level} {title}")
        lines.append("")
        if content_md:
            lines.append(content_md)
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def _compose_architect_chat_parts(responses: list) -> list[str]:
    if not responses:
        return ["Принято. Изменений в документе не потребовалось."]

    updated = [r.section_id for r in responses if getattr(r, "status", "") != "missing"]
    missing = [r.section_id for r in responses if getattr(r, "status", "") == "missing"]

    parts: list[str] = []
    if updated:
        parts.append(f"Обновил разделы ТЗ: {', '.join(updated)}.")
    if missing:
        parts.append(
            "Нужны дополнительные данные по разделам: "
            f"{', '.join(missing)}. Добавил уточняющие действия."
        )

    return parts or ["Принято. Изменений в документе не потребовалось."]


async def _publish_status(
    redis_client: aredis.Redis,
    channel_name: str,
    chat_id: int,
    status: str,
    step: str,
    progress: int,
) -> None:
    await redis_client.publish(
        channel_name,
        json.dumps(
            {
                "type": EventType.GENERATION_STATUS,
                "chat_id": chat_id,
                "status": status,
                "step": step,
                "progress": progress,
            },
            ensure_ascii=False,
        ),
    )


async def _run_orchestrator_message(
    project_id: int,
    user_input: str,
    attachments: list[Attachment],
) -> dict:
    orchestrator = broker.state.orchestrator
    deps: OrchestratorDeps = broker.state.deps

    result = await orchestrator.run(project_id, user_input, attachments)
    if deps.save_document_updates and result.doc_updates:
        await deps.save_document_updates(project_id, result.doc_updates)

    return {
        "chat_text": result.chat_text,
        "chat_parts": result.chat_parts,
        "doc_updates": [item.model_dump(mode="json") for item in result.doc_updates],
        "pending_conflicts": [item.model_dump(mode="json") for item in result.pending_conflicts],
    }


async def _run_tracked_generation(
    *,
    project_id: int,
    user_id: int,
    user_input: str,
    attachments: list[Attachment],
    chat_repo: ChatRepository,
    gen_repo: GenerationRepository,
    gkg_repo: GKGRepository,
    redis_client: aredis.Redis,
    storage: StorageWorker,
    config: AppSettings,
    template_type: str | None = None,
) -> dict:
    channel_name = get_channel_name(user_id)
    active_statuses = {
        str(GenerationRunStatus.PENDING),
        str(GenerationRunStatus.INGESTING),
        str(GenerationRunStatus.COMPILING),
    }
    latest = await gen_repo.get_latest_run(project_id)
    if latest is not None and str(latest.status) in active_statuses:
        await redis_client.publish(
            channel_name,
            json.dumps(
                {
                    "type": EventType.ERROR,
                    "chat_id": project_id,
                    "message": "Generation is already running for this chat",
                },
                ensure_ascii=False,
            ),
        )
        return {"chat_text": "", "doc_updates": [], "pending_conflicts": []}

    run = await gen_repo.create_run(chat_id=project_id, user_id=user_id)
    await _publish_status(
        redis_client,
        channel_name,
        project_id,
        str(GenerationRunStatus.PENDING),
        "Генерация поставлена в очередь",
        5,
    )
    await _publish_status(
        redis_client,
        channel_name,
        project_id,
        str(GenerationRunStatus.INGESTING),
        "Обработка источников",
        20,
    )

    try:
        await _publish_status(
            redis_client,
            channel_name,
            project_id,
            str(GenerationRunStatus.INGESTING),
            "Маршрутизация запроса",
            35,
        )
        result = await _run_orchestrator_message(project_id, user_input, attachments)

        await gen_repo.update_status(
            run.id,
            str(GenerationRunStatus.COMPILING),
            step="Сборка документа",
            progress=80,
        )
        await _publish_status(
            redis_client,
            channel_name,
            project_id,
            str(GenerationRunStatus.COMPILING),
            "Сборка документа",
            80,
        )
        await _publish_status(
            redis_client,
            channel_name,
            project_id,
            str(GenerationRunStatus.COMPILING),
            "Сохранение результата",
            90,
        )

        result_key = f"db://tz-results/{project_id}/{run.id}"
        await gen_repo.save_result(run.id, result_key)

        chat_parts = [str(p).strip() for p in (result.get("chat_parts") or []) if str(p).strip()]
        if not chat_parts:
            fallback_text = str(result.get("chat_text") or "ТЗ обновлено").strip()
            chat_parts = [fallback_text or "ТЗ обновлено"]

        for idx, part in enumerate(chat_parts):
            msg = await chat_repo.create_message_async(
                chat_id=project_id,
                text=part,
                is_user_sender=False,
            )
            await redis_client.publish(
                channel_name,
                json.dumps(
                    {
                        "type": EventType.LLM_ANSWER,
                        "id": msg.id,
                        "chat_id": project_id,
                        "text": part,
                        "attachments": [],
                        "created_at": msg.created_at.isoformat(),
                        "is_final": idx == len(chat_parts) - 1,
                    },
                    ensure_ascii=False,
                ),
            )
        await _publish_status(
            redis_client,
            channel_name,
            project_id,
            str(GenerationRunStatus.COMPLETED),
            "Документ готов",
            100,
        )
        return result
    except Exception as exc:
        logger.exception("orchestrator_generation_failed", chat_id=project_id, user_id=user_id)
        await gen_repo.mark_failed(run.id, str(exc))
        await redis_client.publish(
            channel_name,
            json.dumps(
                {
                    "type": EventType.ERROR,
                    "chat_id": project_id,
                    "message": str(exc),
                },
                ensure_ascii=False,
            ),
        )
        raise


@broker.task
@inject
async def process_message_task(
    project_id: int,
    user_id: int,
    user_input: str,
    attachments: list[Attachment],
    chat_repo: FromDishka[ChatRepository],
    gen_repo: FromDishka[GenerationRepository],
    gkg_repo: FromDishka[GKGRepository],
    redis_client: FromDishka[aredis.Redis],
    storage: FromDishka[StorageWorker],
    config: FromDishka[AppSettings],
) -> dict:
    return await _run_tracked_generation(
        project_id=project_id,
        user_id=user_id,
        user_input=user_input,
        attachments=attachments,
        chat_repo=chat_repo,
        gen_repo=gen_repo,
        gkg_repo=gkg_repo,
        redis_client=redis_client,
        storage=storage,
        config=config,
    )


@broker.task(task_name="backend.worker.tasks.orchestrator_tasks:create_tz_from_template_task")
@inject
async def create_tz_from_template_task(
    project_id: int,
    user_id: int,
    template_type: str,
    attachments: list[Attachment],
    comment: str | None = None,
    chat_repo: FromDishka[ChatRepository] = None,  # type: ignore[assignment]
    gen_repo: FromDishka[GenerationRepository] = None,  # type: ignore[assignment]
    gkg_repo: FromDishka[GKGRepository] = None,  # type: ignore[assignment]
    redis_client: FromDishka[aredis.Redis] = None,  # type: ignore[assignment]
    storage: FromDishka[StorageWorker] = None,  # type: ignore[assignment]
    config: FromDishka[AppSettings] = None,  # type: ignore[assignment]
) -> dict:
    """Первичная генерация ТЗ с учетом выбранного шаблона и источников."""
    deps: OrchestratorDeps = broker.state.deps
    if deps.apply_template_structure is not None:
        await deps.apply_template_structure(project_id, template_type)

    prompt = comment or "Сформируй техническое задание по текущей структуре документа и загруженным источникам."
    return await _run_tracked_generation(
        project_id=project_id,
        user_id=user_id,
        user_input=prompt,
        attachments=attachments,
        chat_repo=chat_repo,
        gen_repo=gen_repo,
        gkg_repo=gkg_repo,
        redis_client=redis_client,
        storage=storage,
        config=config,
        template_type=template_type,
    )


@broker.task
@inject
async def update_tz_with_sources_task(
    project_id: int,
    user_id: int,
    attachments: list[Attachment],
    comment: str | None = None,
    chat_repo: FromDishka[ChatRepository] = None,  # type: ignore[assignment]
    gen_repo: FromDishka[GenerationRepository] = None,  # type: ignore[assignment]
    gkg_repo: FromDishka[GKGRepository] = None,  # type: ignore[assignment]
    redis_client: FromDishka[aredis.Redis] = None,  # type: ignore[assignment]
    storage: FromDishka[StorageWorker] = None,  # type: ignore[assignment]
    config: FromDishka[AppSettings] = None,  # type: ignore[assignment]
) -> dict:
    """Обновление существующего ТЗ: новые источники и/или глобальный комментарий."""
    prompt = comment or "Обнови текущее ТЗ с учетом новых материалов."
    return await _run_tracked_generation(
        project_id=project_id,
        user_id=user_id,
        user_input=prompt,
        attachments=attachments,
        chat_repo=chat_repo,
        gen_repo=gen_repo,
        gkg_repo=gkg_repo,
        redis_client=redis_client,
        storage=storage,
        config=config,
    )


@broker.task
async def regenerate_block_task(
    project_id: int,
    block_id: str,
    trigger_reason: str,
) -> dict:
    """Перегенерация конкретного блока — кампейн с одной секцией."""
    deps: OrchestratorDeps = broker.state.deps
    if deps.list_sections is None:
        raise RuntimeError("list_sections callback is not configured")

    sections_raw = await deps.list_sections(project_id)
    target = next((s for s in sections_raw if s[0] == block_id), None)
    if target is None:
        raise RuntimeError(f"Section {block_id} not found")

    sid, title, level, required, context_hint, content_md, is_manual = target
    if is_manual:
        raise RuntimeError(f"Section {block_id} is locked (is_manual=True)")

    from backend.worker.modules.llm_pipeline.steps.behaviors.architect.campaign import (
        ArchitectCampaign, SectionState,
    )

    document = [
        SectionState(
            section_id=s[0],
            title=s[1],
            level=s[2],
            required=s[3],
            context_hint=s[4],
            content_md=s[5],
            is_manual=s[6],
        )
        for s in sections_raw
    ]

    # Форсируем план — только запрошенный блок
    campaign = ArchitectCampaign(
        user_message=f"Перегенерируй раздел: {title}",
        trigger_reason=trigger_reason,
        document=document,
        forced_sections=[block_id]
    )

    responses = await deps.architect.run_campaign(campaign)
    if deps.save_document_updates and responses:
        await deps.save_document_updates(project_id, responses)

    return responses[0].model_dump() if responses else {"status": "nothing_to_update"}


@broker.task
@inject
async def resolve_conflict_task(
    project_id: int,
    user_id: int,
    action_id: str,
    resolution: str,
    chat_repo: FromDishka[ChatRepository] = None,  # type: ignore[assignment]
    redis_client: FromDishka[aredis.Redis] = None,  # type: ignore[assignment]
) -> dict:
    """Пользователь ответил на вопрос — обновляем GKG, запускаем кампейн."""
    deps: OrchestratorDeps = broker.state.deps
    if deps.resolve_pending_action is None:
        raise RuntimeError("resolve_pending_action callback is not configured")
    if deps.list_sections is None:
        raise RuntimeError("list_sections callback is not configured")

    channel_name = get_channel_name(user_id)
    await _publish_status(
        redis_client,
        channel_name,
        project_id,
        str(GenerationRunStatus.PENDING),
        "Применение ответа по pending action",
        10,
    )

    # 1. Записываем решение в GKG
    resolved_nodes = await deps.resolve_pending_action(project_id, action_id, resolution)

    await _publish_status(
        redis_client,
        channel_name,
        project_id,
        str(GenerationRunStatus.INGESTING),
        "Извлечение фактов из ответа пользователя",
        35,
    )

    harvest_text_lines = [resolution]
    for node in resolved_nodes or []:
        harvest_text_lines.append(f"{node.property}: {node.value}")
    harvest_text = "\n".join(part for part in harvest_text_lines if part)

    harvested = await deps.harvester.process_source(
        source_id=f"pending_action_{action_id}",
        text=harvest_text,
        source_meta="pending_action_resolution",
    )

    if harvested:
        embedded = await deps.embedder.execute(harvested)
        judged = await deps.grouping_judge.run(embedded)
        await deps.persist_gkg(project_id, judged.gkg_nodes, judged.pending_conflicts)

    await _publish_status(
        redis_client,
        channel_name,
        project_id,
        str(GenerationRunStatus.COMPILING),
        "Обновление разделов документа",
        75,
    )

    # 3. Запускаем кампейн — architect сам решит что устарело
    from backend.worker.modules.llm_pipeline.steps.behaviors.architect.campaign import (
        ArchitectCampaign, SectionState,
    )

    sections_raw = await deps.list_sections(project_id)
    document = [
        SectionState(
            section_id=s[0],
            title=s[1],
            level=s[2],
            required=s[3],
            context_hint=s[4],
            content_md=s[5],
            is_manual=s[6],
        )
        for s in sections_raw
    ]

    campaign = ArchitectCampaign(
        user_message=f"Пользователь ответил на вопрос: {resolution}",
        trigger_reason="spec_block_affected",
        document=document,
    )

    responses = await deps.architect.run_campaign(campaign)
    if deps.save_document_updates and responses:
        await deps.save_document_updates(project_id, responses)

    chat_parts = _compose_architect_chat_parts(responses)
    for idx, part in enumerate(chat_parts):
        msg = await chat_repo.create_message_async(
            chat_id=project_id,
            text=part,
            is_user_sender=False,
        )
        await redis_client.publish(
            channel_name,
            json.dumps(
                {
                    "type": EventType.LLM_ANSWER,
                    "id": msg.id,
                    "chat_id": project_id,
                    "text": part,
                    "attachments": [],
                    "created_at": msg.created_at.isoformat(),
                    "is_final": idx == len(chat_parts) - 1,
                },
                ensure_ascii=False,
            ),
        )

    await _publish_status(
        redis_client,
        channel_name,
        project_id,
        str(GenerationRunStatus.COMPLETED),
        "Изменения применены",
        100,
    )

    return {"updated_blocks": [r.model_dump() for r in responses]}


@broker.task
async def lock_block_task(
    project_id: int,
    block_id: str,
    content_md: str,
) -> dict:
    """
    Инвариант 5 — ручное редактирование.
    Back-propagation: текст пользователя → факты → GKG.
    Блок помечается is_manual=True.
    """
    deps: OrchestratorDeps = broker.state.deps
    if deps.mark_block_manual is None:
        raise RuntimeError("mark_block_manual callback is not configured")

    # Извлекаем факты из текста через Harvester (один чанк)
    staging_nodes = await deps.harvester.process_source(
        source_id=f"manual_edit_{block_id}",
        text=content_md,
        source_meta=f"Ручная правка блока {block_id}",
    )

    # Записываем в GKG с max приоритетом
    if staging_nodes:
        embedded = await deps.embedder.execute(staging_nodes)
        result = await deps.grouping_judge.run(embedded)  # разрешаем конфликты
        await deps.persist_gkg(project_id, result.gkg_nodes, result.pending_conflicts)

    # Помечаем блок как locked
    await deps.mark_block_manual(project_id, block_id, content_md)
    return {"block_id": block_id, "status": "locked"}


@broker.task
@inject
async def export_tz_task(
    project_id: int,
    user_id: int,
    result_key: str,
    format: str,
    gen_repo: FromDishka[GenerationRepository],
    gkg_repo: FromDishka[GKGRepository],
    storage: FromDishka[StorageWorker],
    config: FromDishka[AppSettings],
    redis_client: FromDishka[aredis.Redis],
) -> dict:
    channel_name = get_channel_name(user_id)

    try:
        run = await gen_repo.get_run_by_result_key(project_id, result_key)
        if run is None:
            raise RuntimeError("Generation result not found")

        payload = await gkg_repo.build_tz_result_payload(project_id)
        sections = payload.get("sections") if isinstance(payload, dict) else None
        if not isinstance(sections, list) or len(sections) == 0:
            raise RuntimeError("No document sections available for export")

        markdown_content = _render_sections_to_markdown(sections)
        exporter = get_exporter(format)
        file_bytes = await exporter.export(markdown_content)

        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        export_key = f"exports/{project_id}/tz-{run.id}-{ts}.{exporter.file_extension}"
        await storage.put_object(
            bucket=config.storage.BUCKET_NAME,
            key=export_key,
            data=file_bytes,
            content_type=exporter.content_type,
        )

        await redis_client.publish(
            channel_name,
            json.dumps(
                {
                    "type": EventType.EXPORT_READY,
                    "chat_id": project_id,
                    "export_key": export_key,
                    "format": format,
                },
                ensure_ascii=False,
            ),
        )

        return {
            "status": "ok",
            "export_key": export_key,
            "format": format,
        }
    except Exception as exc:
        logger.exception(
            "export_tz_failed",
            chat_id=project_id,
            user_id=user_id,
            result_key=result_key,
            format=format,
        )
        await redis_client.publish(
            channel_name,
            json.dumps(
                {
                    "type": EventType.ERROR,
                    "chat_id": project_id,
                    "message": f"Export failed: {exc}",
                },
                ensure_ascii=False,
            ),
        )
        raise
