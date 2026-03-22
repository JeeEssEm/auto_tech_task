from prisma import Prisma
from prisma.models import Chat, Message, Attachment, ParsedAttachment
from prisma.types import (
    ChatWhereInput, ChatCreateInput, MessageCreateInput, AttachmentCreateInput, ChatWhereInput,
    MessageWhereInput, MessageInclude, AttachmentInclude, AttachmentWhereInput, ChatRelationFilter,
    MessageRelationFilter, MessageUpdateInput, MessageWhereUniqueInput, AttachmentWhereUniqueInput,
    AttachmentUpdateManyWithoutRelationsInput, AttachmentUpdateInput, ParsedAttachmentCreateInput
)

from backend.app.domain.chat.value_objects.types import ChatTemplate, MessageSender, ParsingStatus


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

    async def create_orphan_attachment_async(
            self, file_id: str, file_type: str, file_name: str, file_size: float, user_id: int
    ):
        return await self._db.attachment.create(
            AttachmentCreateInput(
                id=file_id,
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                owner_id=user_id,
                parsing_status=ParsingStatus.PENDING
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

    async def get_chat_template_async(self, chat_id: int) -> ChatTemplate:
        chat = await self._db.chat.find_unique(where={"id": chat_id})
        if chat is None or not chat.template:
            return ChatTemplate.FREE
        try:
            return ChatTemplate(chat.template)
        except ValueError:
            return ChatTemplate.FREE

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
        return await self._db.attachment.find_many(
            where={
                "id": {
                    "in": attachment_ids
                }
            }
        )

    async def get_attachments_with_parsed_async(self, attachment_ids: list[str]) -> list[Attachment]:
        return await self._db.attachment.find_many(
            where={
                "id": {
                    "in": attachment_ids
                }
            },
            include={"parsed_attachment": True}
        )

    async def check_all_attachments_belong_to_user_async(
            self, user_id: int, attachment_ids: list[str]
    ) -> bool:
        if not attachment_ids:
            return True
        count = await self._db.attachment.count(
            where=AttachmentWhereInput(
                id={"in": attachment_ids},
                owner_id=user_id,
            )
        )
        return count == len(attachment_ids)

    async def change_attachment_parsing_status_async(
            self, status: ParsingStatus, attachment_id: str
    ) -> ParsedAttachment | None:
        return await self._db.attachment.update(
            data=AttachmentUpdateInput(parsing_status=status),
            where=AttachmentWhereUniqueInput(id=attachment_id)
        )

    async def create_parsed_attachment(self, parsed_attachment_id: str, raw_attachment_id: str) -> ParsedAttachment:
        return await self._db.parsedattachment.create(
            ParsedAttachmentCreateInput(id=parsed_attachment_id, raw_attachment_id=raw_attachment_id)
        )

    async def get_chat_attachments_with_parsed_async(self, chat_id: int) -> list[Attachment]:
        return await self._db.attachment.find_many(
            where={
                "message": {"is": {"chat_id": chat_id}},
                "parsing_status": "SUCCESS",
            },
            include={"parsed_attachment": True}
        )
