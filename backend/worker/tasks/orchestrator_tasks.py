import asyncio
import json

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
from backend.worker.modules.llm_pipeline.orchestrator.nodes import OrchestratorDeps
from backend.worker.modules.llm_pipeline.orchestrator.state import Attachment

logger = structlog.get_logger(__name__)


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

        result_payload = await gkg_repo.build_tz_result_payload(project_id, template_type=template_type)
        result_key = f"tz-results/{project_id}/{run.id}.json"
        await storage.put_object(
            bucket=config.storage.BUCKET_NAME,
            key=result_key,
            data=json.dumps(result_payload, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
        )
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


@broker.task
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
    trigger_reason: str,  # explicit_regen_request | spec_block_affected
) -> dict:
    """
    Инвариант 2 — перегенерация конкретного блока.
    Прямой вызов Architect, без IntentRouter и Harvester.
    """
    deps: OrchestratorDeps = broker.state.deps
    if deps.build_document_snapshot is None:
        raise RuntimeError("build_document_snapshot callback is not configured")

    snapshot = await deps.build_document_snapshot(
        project_id=project_id,
        block_id=block_id,
        trigger_reason=trigger_reason,
    )
    response = await deps.architect.run(snapshot)
    return response.model_dump()


@broker.task
async def resolve_conflict_task(
    project_id: int,
    action_id: str,
    resolution: str,        # выбранный вариант или свой текст
) -> dict:
    """
    Инвариант pending_action — пользователь ответил на вопрос системы.
    GKG update → затронутые блоки → Architect для каждого.
    """
    deps: OrchestratorDeps = broker.state.deps
    if deps.resolve_pending_action is None:
        raise RuntimeError("resolve_pending_action callback is not configured")

    # 1. Записываем решение в GKG с authority_weight=1.0
    affected_nodes = await deps.resolve_pending_action(
        project_id, action_id, resolution
    )

    # 2. Находим затронутые блоки
    snapshots = await deps.get_affected_sections(project_id, affected_nodes)

    # 3. Регенерируем параллельно
    responses = await asyncio.gather(*[
        deps.architect.run(snap) for snap in snapshots
    ])
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
