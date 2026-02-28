import asyncio
import json

import structlog
from dishka.integrations.taskiq import FromDishka, inject

import redis.asyncio as aredis

from backend.app.infrastructure.utils.channels import get_channel_name
from backend.worker.broker import broker
from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.domain.chat.value_objects.types import EventType, GenerationStatus

logger = structlog.get_logger(__name__)


@broker.task(task_name="generate_tz")
@inject
async def generate_tz_task(
        chat_id: int,
        user_id: int,
        prompt: str,
        chat_repo: FromDishka[ChatRepository],
        redis_client: FromDishka[aredis.Redis]
):
    channel_name = get_channel_name(user_id)
    log = logger.bind(chat_id=chat_id, user_id=user_id)

    try:
        log.info("generate_tz_started")
        await asyncio.sleep(2)
        generated_text = f"Сгенерированное ТЗ по запросу: {prompt}"

        await redis_client.publish(
            channel_name,
            create_generation_status_message(chat_id, GenerationStatus.ANALYZING_DATA)
        )

        msg = await chat_repo.create_message_async(
            chat_id=chat_id,
            text=generated_text,
            is_user_sender=False
        )
        await redis_client.publish(
            channel_name,
            create_generation_status_message(chat_id, GenerationStatus.BUILDING_GRAPH)
        )

        await asyncio.sleep(5)

        await redis_client.publish(
            channel_name,
            create_generation_status_message(chat_id, GenerationStatus.MERGING_DATA_SOURCES)
        )

        await asyncio.sleep(5)

        await redis_client.publish(
            channel_name,
            create_generation_status_message(chat_id, GenerationStatus.VERIFYING_DATA)
        )

        await asyncio.sleep(5)

        await redis_client.publish(
            channel_name,
            json.dumps({
                "id": msg.id,
                "chat_id": chat_id,
                "text": generated_text,
                "type": EventType.LLM_ANSWER,
                "created_at": msg.created_at.isoformat()
            })
        )
        log.info("generate_tz_completed", message_id=msg.id)

    except Exception:
        log.exception("generate_tz_failed")
        await redis_client.publish(
            channel_name,
            json.dumps({
                "type": EventType.ERROR,
                "chat_id": chat_id,
            })
        )


def create_generation_status_message(chat_id: int, status: GenerationStatus):
    return json.dumps({
        "chat_id": chat_id,
        "type": EventType.GENERATION_STATUS,
        "status": status
    })
