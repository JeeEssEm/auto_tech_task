import datetime
import uuid
from typing import AsyncGenerator

from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.infrastructure.storage import StorageWorker

from backend.app.web.schemas.user import SignupUser, LoginUser
from backend.app.domain.user.exceptions import UserAlreadyExists, UserNotFound, InvalidCredentials
from backend.app.infrastructure.config import AppSettings


class ChatService:
    def __init__(self, repo: ChatRepository, storage: StorageWorker, config: AppSettings):
        self._chat_repo = repo
        self._storage = storage
        self._bucket_name = config.storage.BUCKET_NAME

    async def get_messages_async(self, user_id: int, chat_id: int):
        if await self._chat_repo.check_user_has_chat_async(user_id, chat_id):
            return self._chat_repo.get_chat_messages_async(chat_id)

        raise Exception() # TODO: сделать нормальное ForbiddenException

    async def get_attachment_async(self, user_id: int, attachment_id: str):
        if await self._chat_repo.check_user_has_attachment_async(user_id, attachment_id):
            return # TODO

        raise Exception() # TODO:

    async def upload_attachment(self, user_id: int, content_type: str, file_size: float, file_stream: AsyncGenerator[bytes, None]):
        attachment_id = str(uuid.uuid4().hex)

        await self._storage.upload_stream(
            bucket=self._bucket_name,
            key=attachment_id,
            stream=file_stream,
            content_type=content_type
        )
        # не делаем запись, если не смогли загрузить файл в S3
        await self._chat_repo.create_orphan_attachment_async(
            file_id=attachment_id,
            file_type=content_type,
            file_size=file_size,
            user_id=user_id
        )
        return attachment_id
