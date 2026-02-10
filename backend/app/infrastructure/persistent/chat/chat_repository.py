from prisma import Prisma
from prisma.models import Chat, Message, Attachment
from prisma.enums import Sender
from prisma.types import (
    ChatWhereInput, ChatCreateInput, MessageCreateInput, AttachmentCreateInput, ChatWhereInput,
    MessageWhereInput, MessageInclude, AttachmentInclude, AttachmentWhereInput, ChatRelationFilter,
    MessageRelationFilter
)


class ChatRepository:
    def __init__(self, db: Prisma):
        self._db = db

    async def create_chat_async(self, user_id: int) -> Chat:
        return await self._db.chat.create(ChatCreateInput(owner_id=user_id, name="Unknown"))

    async def create_message_async(
            self,
            chat_id: int,
            text: str,
            is_user_sender: bool
    ) -> Message:
        sender = Sender.LLM
        if is_user_sender:
            sender = Sender.USER
        return await self._db.message.create(MessageCreateInput(chat_id=chat_id, body=text, sender=sender))

    async def create_attachment_async(
            self,
            file_id: str,
            message_id: int,
            file_type: str,
            file_size: float
    ) -> Attachment:
        return await self._db.attachment.create(
            AttachmentCreateInput(
                id=file_id,
                message_id=message_id,
                file_type=file_type,
                file_size=file_size
            )
        )

    async def create_orphan_attachment_async(self, file_id: str, file_type: str, file_size: float, user_id: int):
        return await self._db.attachment.create(
            AttachmentCreateInput(
                id=file_id,
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
            include=MessageInclude(attachments=True)
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
            where=AttachmentWhereInput(
                id=attachment_id,
                message={
                    "is": {
                        "chat": {
                            "is": {
                                "owner_id": user_id
                            }
                        }
                    }
                }
            )
        )
        return attachment is not None

    async def get_attachment_async(self, attachment_id: str) -> Attachment:
        return await self._db.attachment.find_first(where=AttachmentWhereInput(id=attachment_id))
