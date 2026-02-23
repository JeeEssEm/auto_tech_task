from prisma import Prisma
from prisma.models import Chat, Message, Attachment
from prisma.types import (
    ChatWhereInput, ChatCreateInput, MessageCreateInput, AttachmentCreateInput, ChatWhereInput,
    MessageWhereInput, MessageInclude, AttachmentInclude, AttachmentWhereInput, ChatRelationFilter,
    MessageRelationFilter, MessageUpdateInput, MessageWhereUniqueInput, AttachmentWhereUniqueInput,
    AttachmentUpdateManyWithoutRelationsInput
)

from backend.app.domain.chat.value_objects.types import ChatTemplate, MessageSender


class ChatRepository:
    def __init__(self, db: Prisma):
        self._db = db

    async def create_chat_async(self, user_id: int, name: str, chat_template: ChatTemplate) -> Chat:
        return await self._db.chat.create(
            ChatCreateInput(
                owner_id=user_id,
                name=name,
                template=str(chat_template.value)
            )
        )

    async def create_message_async(
            self,
            chat_id: int,
            text: str | None,
            is_user_sender: bool
    ) -> Message:
        sender = MessageSender.LLM
        if is_user_sender:
            sender = MessageSender.USER
        return await self._db.message.create(MessageCreateInput(chat_id=chat_id, body=text, sender=str(sender.value)))

    async def add_attachments_to_message_async(
            self,
            attachment_ids: list[str],
            message_id: int
    ):
        await self._db.message.update(
            where=MessageWhereUniqueInput(id=message_id),
            data=MessageUpdateInput(
                attachments=AttachmentUpdateManyWithoutRelationsInput(
                    connect=[
                        AttachmentWhereUniqueInput(id=attachment_id)
                        for attachment_id in attachment_ids
                    ]
                )
            )
        )

    async def create_orphan_attachment_async(self, file_id: str, file_type: str, file_name: str, file_size: float, user_id: int):
        return await self._db.attachment.create(
            AttachmentCreateInput(
                id=file_id,
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                owner_id=user_id
            )
        )

    async def get_user_chats_async(self, user_id: int, page: int = 1, limit: int = 5) -> list[Chat]:
        return await self._db.chat.find_many(
            take=limit,
            skip=(page - 1) * limit,
            where=ChatWhereInput(owner_id=user_id)
        )

    async def get_chat_messages_async(self, chat_id: int) -> list[Message]:
        # TODO: по-хорошему надо пагинацию делать, чтоб гигантский json не тащить
        return await self._db.message.find_many(
            where=MessageWhereInput(chat_id=chat_id),
            include=MessageInclude(attachments=True),
            order={"created_at": "asc"}
        )

    async def check_user_has_chat_async(self, user_id: int, chat_id: int) -> bool:
        return await self._db.chat.find_first(where=ChatWhereInput(id=chat_id, owner_id=user_id)) is not None

    async def check_user_has_message_async(self, user_id: int, message_id: int) -> bool:
        return await self._db.message.find_first(
            where=MessageWhereInput(
                id=message_id,
                chat={
                    "is": {
                        "owner_id": user_id
                    }
                }
            )
        ) is not None

    async def check_user_has_attachment_async(self, user_id: int, attachment_id: str) -> bool:
        attachment = await self._db.attachment.find_first(
            where=AttachmentWhereInput(owner_id=user_id, id=attachment_id)
        )
        return attachment is not None

    async def get_attachment_async(self, attachment_id: str) -> Attachment | None:
        return await self._db.attachment.find_first(where=AttachmentWhereInput(id=attachment_id))

    async def get_attachments_async(self, attachment_ids: list[str]) -> list[Attachment]:
        return await self._db.attachment.find_many(where={
            "id": {
                "in": attachment_ids
            }
        })
