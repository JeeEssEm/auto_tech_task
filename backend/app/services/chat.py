import uuid
from typing import AsyncGenerator

from click import prompt

from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.infrastructure.storage import StorageWorker
from backend.app.infrastructure.config import AppSettings

from backend.app.web.exceptions import CannotCreateEmptyChat, AttachmentNotFound, ChatNotFound, NotEnoughPermissions
from backend.app.web.schemas.chat import SmallChat, Message as MessageSchema, Attachment
from backend.app.domain.chat.value_objects.types import ChatTemplate, MessageSender

from backend.worker.tasks.parse_file import parse_file_task
from backend.worker.tasks.stupid_answer_task import generate_tz_task


class ChatService:
    def __init__(self, repo: ChatRepository, storage: StorageWorker, config: AppSettings):
        self._chat_repo = repo
        self._storage = storage
        self._bucket_name = config.storage.BUCKET_NAME

    async def get_messages_async(self, user_id: int, chat_id: int) -> list[MessageSchema]:
        if await self._chat_repo.check_user_has_chat_async(user_id, chat_id):
            return [
                MessageSchema(
                    id=msg.id,
                    sender=MessageSender(msg.sender.strip()),
                    text=msg.body,
                    attachments=[
                        Attachment(
                            key=attach.id, file_size=attach.file_size, file_type=attach.file_type,
                            file_name=attach.file_name
                        )
                        for attach in msg.attachments
                    ],
                    created_at=msg.created_at
                )
                for msg in await self._chat_repo.get_chat_messages_async(chat_id)
            ]

        raise ChatNotFound(chat_id)

    async def get_attachment_async(self, user_id: int, attachment_id: str):
        if await self._chat_repo.check_user_has_attachment_async(user_id, attachment_id):
            return await self._storage.get_object_stream_with_meta(bucket=self._bucket_name, key=attachment_id)

        raise AttachmentNotFound(attachment_id)

    async def upload_attachment(self, user_id: int, content_type: str, filename: str, file_stream: AsyncGenerator[bytes, None]):
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
                file_name=filename,
                user_id=user_id
            )

            await parse_file_task.kiq(user_id=user_id, attachment_id=attachment_id, filename=filename)

            return attachment_id
        except Exception as e:
            # TODO: добавить логгирование
            await self._storage.remove_object(bucket=self._bucket_name, key=attachment_id)
            raise

    async def create_chat_async(
            self,
            chat_name: str,
            owner_id: int,
            attachment_ids: list[str],
            template_type: ChatTemplate,
            init_message: str | None
    ) -> int:
        if len(attachment_ids) == 0 and not init_message:
            raise CannotCreateEmptyChat()

        # TODO: проверка, что все attachment_id есть в бд
        # TODO: проверка, что все attachment_id принадлежат ЭТОМУ юзеру

        chat = await self._chat_repo.create_chat_async(owner_id, chat_name, chat_template=template_type)
        message = await self._chat_repo.create_message_async(chat_id=chat.id, text=init_message, is_user_sender=True)
        await self._chat_repo.add_attachments_to_message_async(attachment_ids, message.id)

        return chat.id

    async def get_user_chats_async(self, user_id: int, page: int, limit: int) -> list[SmallChat]:
        chats = await self._chat_repo.get_user_chats_async(user_id, page=page, limit=limit)
        return [SmallChat(id=chat.id, name=chat.name, template=ChatTemplate(chat.template)) for chat in chats]

    async def create_message_async(
            self, user_id: int, chat_id: int, text: str | None, attachment_ids: list[str]
    ) -> MessageSchema:
        # TODO: проверить существование attachment_id и их принадлежность к юзеру
        if not await self._chat_repo.check_user_has_chat_async(user_id, chat_id):
            raise ChatNotFound(chat_id)

        message = await self._chat_repo.create_message_async(chat_id, text, is_user_sender=True)
        await self._chat_repo.add_attachments_to_message_async(attachment_ids, message.id)
        attachments = await self._chat_repo.get_attachments_async(attachment_ids)

        if text:
            await generate_tz_task.kiq(chat_id=chat_id, user_id=user_id, prompt=text)

        return MessageSchema(
            id=message.id,
            sender=MessageSender.USER,
            text=text,
            attachments=[
                Attachment(
                    key=attach.id, file_type=attach.file_type, file_size=attach.file_size, file_name=attach.file_name
                )
                for attach in attachments
            ],
            created_at=message.created_at
        )
