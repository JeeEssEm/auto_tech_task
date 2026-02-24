import asyncio
import json

from dishka.integrations.taskiq import FromDishka, inject

import redis.asyncio as aredis

from backend.app.infrastructure.utils.channels import get_channel_name
from backend.worker.broker import broker
from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.domain.chat.value_objects.types import EventTypes


@broker.task(task_name="generate_tz")
@inject
async def generate_tz_task(
        chat_id: int,
        user_id: int,
        prompt: str,
        chat_repo: FromDishka[ChatRepository],
        redis_client: FromDishka[aredis.Redis]
):
    try:
        await asyncio.sleep(2)
        generated_text = f"Сгенерированное ТЗ по запросу: {prompt}"

        msg = await chat_repo.create_message_async(
            chat_id=chat_id,
            text=generated_text,
            is_user_sender=False
        )
        await redis_client.publish(
            get_channel_name(user_id),
            json.dumps({
                "id": msg.id,
                "text": generated_text,
                "type": EventTypes.LLM_ANSWER,
                "created_at": msg.created_at.isoformat()
            })
        )

    except Exception as e:
        await redis_client.publish(
            get_channel_name(user_id),
            json.dumps({
                "message": str(e),
                "type": EventTypes.ERROR
            })
        )
