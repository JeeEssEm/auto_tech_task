import json

from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse

from dishka.integrations.fastapi import FromDishka, DishkaRoute

from backend.app.domain.user import User
from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.infrastructure.persistent.user import UserRepository
from backend.app.infrastructure.persistent.generation import GenerationRepository
from backend.app.services import ChatService
from backend.app.infrastructure.storage import StorageWorker
from backend.app.web.exceptions import AttachmentFieldIsMissing
from backend.app.web.schemas.chat import CreateChat, SmallChat, CreateMessage
from backend.app.infrastructure.auth.typed_roles import StaffUser, SuperUser, AuthenticatedUser
from backend.app.web.schemas.chat.chat import Message

router = APIRouter(prefix="/chat", route_class=DishkaRoute, tags=["chat"])


@router.post("/create")
async def create_chat(
        user: FromDishka[AuthenticatedUser],
        chat_service: FromDishka[ChatService],
        form_data: CreateChat
) -> int:
    return await chat_service.create_chat_async(
        chat_name=form_data.name,
        owner_id=user.id,
        attachment_ids=form_data.attachment_ids,
        init_message=form_data.init_user_message,
        template_type=form_data.template_type
    )


@router.get("/all")
async def get_user_chats(
        user: FromDishka[AuthenticatedUser],
        chat_service: FromDishka[ChatService],
        page: int = 1,
        limit: int = 10
) -> list[SmallChat]:
    # TODO: добавить сортировку по дате последнего сообщения!
    return await chat_service.get_user_chats_async(user.id, page, limit)


@router.post("/files/upload")
async def upload_file(
        file_name: str,
        request: Request,
        user: FromDishka[AuthenticatedUser],
        service: FromDishka[ChatService]
):
    # TODO: вынести ограничение на максимальный размер загружаемого файла в конфиг
    # TODO: добавить ограничение на тип файла
    content_type = request.headers.get("content-type")

    if not file_name:
        raise AttachmentFieldIsMissing("file_name")

    return await service.upload_attachment(user.id, content_type, file_name, request.stream())


@router.get("/files")
async def get_file(
        file_id: str,
        user: FromDishka[AuthenticatedUser],
        chat_service: FromDishka[ChatService],
):
    stream, meta = await chat_service.get_attachment_async(user.id, file_id)

    return StreamingResponse(
        stream,
        media_type=meta["content_type"],
        headers={
            "Content-Length": str(meta["content_length"]),
            "ETag": meta["etag"],
        },
    )


@router.get("/{chat_id}/parsed-files")
async def get_parsed_files(
        chat_id: int,
        user: FromDishka[AuthenticatedUser],
        chat_service: FromDishka[ChatService],
):
    return await chat_service.get_parsed_attachments_async(user.id, chat_id)


@router.post("/{chat_id}/messages")
async def create_message(
        chat_id: int,
        form_data: CreateMessage,
        user: FromDishka[AuthenticatedUser],
        chat_service: FromDishka[ChatService]
) -> Message:
    return await chat_service.create_message_async(
        user_id=user.id,
        chat_id=chat_id,
        text=form_data.text,
        attachment_ids=form_data.attachment_ids
    )


@router.get("/{chat_id}/messages")
async def get_chat_messages(
        chat_id: int,
        user: FromDishka[AuthenticatedUser],
        chat_service: FromDishka[ChatService]
) -> list[Message]:
    # TODO: добавить пагинацию
    return await chat_service.get_messages_async(user_id=user.id, chat_id=chat_id)
