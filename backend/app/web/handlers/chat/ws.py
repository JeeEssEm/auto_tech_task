import asyncio
import json

from fastapi import APIRouter
from fastapi.websockets import WebSocket, WebSocketDisconnect

import redis.asyncio as aredis
import redis.client

from dishka.integrations.fastapi import inject, FromDishka

from backend.app.domain.chat.value_objects.types import EventTypes
from backend.app.infrastructure.persistent.user import UserRepository
from backend.app.infrastructure.utils.channels import get_channel_name


router = APIRouter(prefix="/chat", tags=["chat", "websocket"])


async def task_status_listener(pubsub: redis.client.PubSub, websocket: WebSocket):
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = json.loads(message["data"])
            match data["type"]:
                case EventTypes.LLM_ANSWER:
                    await websocket.send_json(data)
                case EventTypes.GENERATION_STATUS:
                    await websocket.send({})
    except asyncio.CancelledError:
        pass


@router.websocket("/ws")
@inject
async def update_chat_state(
        websocket: WebSocket,
        user_repo: FromDishka[UserRepository],
        redis_client: FromDishka[aredis.Redis]
):
    await websocket.accept()

    session_id = websocket.cookies.get("session_id")
    if not session_id:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    user = await user_repo.get_user_by_session_id_async(session_id)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    channel_name = get_channel_name(user.id)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel_name)
    listener_task = asyncio.create_task(task_status_listener(pubsub, websocket))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        listener_task.cancel()
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()
