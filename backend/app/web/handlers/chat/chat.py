import uuid

from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse

from dishka.integrations.fastapi import FromDishka, DishkaRoute

from backend.app.services import ChatService
from backend.app.infrastructure.storage import StorageWorker

router = APIRouter(prefix="/chat", route_class=DishkaRoute, tags=["chat"])


@router.post("/create")
async def create_chat():
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
async def upload_file(request: Request, service: FromDishka[ChatService], content_length: int = Header(...)):
    # TODO: добавить ограничение на максимальный размер загружаемого файла:
    # проверка на максимальный размер должна быть и внутри загрузки в S3! Нельзя полагаться только на Content-Length!
    # Ограничение на размер файла лучше вынести в константу, например, в конфиг
    # TODO: добавить ограничение на тип файла
    content_type = request.headers.get("content-type")

    return await service.upload_attachment(1, content_type, content_length, request.stream())


@router.get("/get-file/{etag}")
async def get_file(etag: str, storage: FromDishka[StorageWorker]):
    try:
        stream, meta = await storage.get_object_stream_with_meta(bucket="user-files", key=etag)

        return StreamingResponse(
            stream,
            media_type=meta["content_type"],
            headers={
                "Content-Length": str(meta["content_length"]),
                "ETag": meta["etag"],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")
