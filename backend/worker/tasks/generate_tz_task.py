import json
from typing import Any

import structlog
from dishka.integrations.taskiq import FromDishka, inject

import redis.asyncio as aredis

from backend.app.domain.chat.value_objects.types import (
    EventType,
    GenerationRunStatus,
)
from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.infrastructure.persistent.generation import GenerationRepository
from backend.app.infrastructure.storage import StorageWorker
from backend.app.infrastructure.utils.channels import get_channel_name
from backend.worker.broker import broker
from backend.worker.modules.machine_learning.interface import DataSource
from backend.worker.modules.machine_learning.mock_adapter import MockITZPipelineAdapter

logger = structlog.get_logger(__name__)


@broker.task(task_name="generate_tz")
@inject
async def generate_tz_task(
        chat_id: int,
        user_id: int,
        prompt: str,
        chat_repo: FromDishka[ChatRepository],
        gen_repo: FromDishka[GenerationRepository],
        redis_client: FromDishka[aredis.Redis],
        storage: FromDishka[StorageWorker],
        config: FromDishka[AppSettings],
):
    """
    Оркестрация генерации ТЗ через LLM-пайплайн.

    Последовательность:
      1. Создаём запись GenerationRun (PENDING)
      2. ingest_sources  — извлечение данных из источников
      3. Сохраняем промежуточный стейт адаптера в БД
      4. compile_document — сборка итогового ТЗ
      5. Сохраняем результат в S3 и БД
      6. Публикуем финальное уведомление в Redis (LLM_ANSWER)

    Notifier-callback на каждом шаге:
      - сначала пишет в БД (offline-first, фронт может GET-ом получить статус)
      - потом публикует в Redis PubSub (эфемерное WS-уведомление)
    """
    channel_name = get_channel_name(user_id)
    log = logger.bind(chat_id=chat_id, user_id=user_id)

    run = await gen_repo.create_run(chat_id=chat_id, user_id=user_id)
    log = log.bind(run_id=run.id)

    async def notifier_callback(event_name: str, payload: dict[str, Any]) -> None:
        step_message = payload.get("message", "")
        progress = payload.get("progress", 0)

        await gen_repo.update_status(
            run_id=run.id,
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

    try:
        log.info("generate_tz_started")

        # --- Phase 1: Ingest ---
        await gen_repo.update_status(
            run.id, GenerationRunStatus.INGESTING, step="Начинаем обработку источников", progress=0
        )

        adapter = MockITZPipelineAdapter()
        adapter.attach_notifier(notifier_callback)

        sources = [DataSource(id="user_prompt", type="text", content=prompt)]
        conflicts = await adapter.ingest_sources(sources)

        await gen_repo.save_state(run.id, json.dumps(adapter.save_state()))
        log.info("ingest_completed", conflicts_count=len(conflicts))

        # --- Phase 2: Compile ---
        await gen_repo.update_status(
            run.id, GenerationRunStatus.COMPILING, step="Собираем итоговый документ", progress=0
        )

        result = await adapter.compile_document()

        # --- Phase 3: Persist result ---
        result_json = result.model_dump_json()
        result_key = f"tz-results/{chat_id}/{run.id}.json"

        await storage.put_object(
            bucket=config.storage.BUCKET_NAME,
            key=result_key,
            data=result_json.encode("utf-8"),
            content_type="application/json",
        )

        await gen_repo.save_result(run.id, result_key)

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
                "text": "Йоу, готово, босс",
                "type": EventType.LLM_ANSWER,
                "created_at": msg.created_at.isoformat(),
            }),
        )

        log.info("generate_tz_completed", message_id=msg.id, result_key=result_key)

    except Exception:
        log.exception("generate_tz_failed")
        await gen_repo.mark_failed(run.id, "Internal pipeline error")
        await redis_client.publish(
            channel_name,
            json.dumps({
                "type": EventType.ERROR,
                "chat_id": chat_id,
            }),
        )
