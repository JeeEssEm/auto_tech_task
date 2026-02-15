from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from backend.app.domain.chat.value_objects.types import ChatTemplate, MessageSender
from backend.app.web.schemas.chat.attachments import Attachment


class CreateChat(BaseModel):
    name: str = Field(max_length=128)
    init_user_message: str | None
    template_type: ChatTemplate
    attachment_ids: list[str]


class SmallChat(BaseModel):
    id: int
    template: ChatTemplate
    name: str


class Message(BaseModel):
    id: int
    sender: MessageSender
    text: str | None
    attachments: list[Attachment]
    created_at: datetime


class CreateMessage(BaseModel):
    text: str | None
    attachment_ids: list[str]

    @model_validator(mode="after")
    def validate_message(self) -> "CreateMessage":
        if not self.text and len(self.attachment_ids) == 0:
            raise ValueError("Message must have text, or attachments, or both!")
        return self
