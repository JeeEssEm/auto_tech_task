from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse

from dishka.integrations.fastapi import FromDishka, DishkaRoute

from backend.app.domain.user import User
from backend.app.infrastructure.persistent.user import UserRepository
from backend.app.services import ChatService
from backend.app.infrastructure.storage import StorageWorker
from backend.app.infrastructure.auth.typed_roles import StaffUser, SuperUser, AuthenticatedUser

router = APIRouter(prefix="/chat", route_class=DishkaRoute, tags=["chat"])


@router.post("/create")
async def create_chat(staff: FromDishka[AuthenticatedUser]):
    pass


@router.get("/all")
async def get_user_chats():
    pass


@router.post("/{chat_id}/messages")
async def create_message():
    pass


@router.get("/{chat_id}/messages")
async def get_chat_messages():
    pass


@router.post("/{chat_id}/messages/{message_id}")
async def add_attachment_to_message():
    pass


@router.post("/files/upload")
async def upload_file(
        request: Request,
        user: FromDishka[AuthenticatedUser],
        service: FromDishka[ChatService]
):
    # TODO: вынести ограничение на максимальный размер загружаемого файла в конфиг
    # TODO: добавить ограничение на тип файла
    content_type = request.headers.get("content-type")

    return await service.upload_attachment(user.id, content_type, request.stream())


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
