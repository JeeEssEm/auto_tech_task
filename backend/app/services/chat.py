import uuid
from typing import AsyncGenerator

from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.infrastructure.storage import StorageWorker

from backend.app.infrastructure.config import AppSettings
from backend.app.web.exceptions import NotEnoughRightsToCheckAttachment, AttachmentNotFound


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
            return await self._storage.get_object_stream_with_meta(bucket=self._bucket_name, key=attachment_id)

        raise AttachmentNotFound(attachment_id)

    async def upload_attachment(self, user_id: int, content_type: str, file_stream: AsyncGenerator[bytes, None]):
        attachment_id = str(uuid.uuid4().hex)

        etag, actual_size = await self._storage.upload_stream(
            bucket=self._bucket_name,
            key=attachment_id,
            stream=file_stream,
            content_type=content_type
        )
        # не делаем запись, если не смогли загрузить файл в S3
        try:
            await self._chat_repo.create_orphan_attachment_async(
                file_id=attachment_id,
                file_type=content_type,
                file_size=actual_size,
                user_id=user_id
            )
            return attachment_id
        except Exception as e:
            # TODO: добавить логгирование
            await self._storage.remove_object(bucket=self._bucket_name, key=attachment_id)
            raise
