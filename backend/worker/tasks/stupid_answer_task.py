import asyncio
from dishka.integrations.taskiq import FromDishka, inject

from backend.worker.broker import broker
from backend.app.infrastructure.persistent.chat import ChatRepository


@broker.task(task_name="generate_tz")
@inject
async def generate_tz_task(
        chat_id: int,
        user_id: int,
        prompt: str,
        chat_repo: FromDishka[ChatRepository]
):
    try:
        await asyncio.sleep(10)
        generated_text = f"Сгенерированное ТЗ по запросу: {prompt}"

        await chat_repo.create_message_async(
            chat_id=chat_id,
            text=generated_text,
            is_user_sender=False
        )

        return {"status": "success", "chat_id": chat_id}

    except Exception as e:
        return {"status": "error", "reason": str(e)}
