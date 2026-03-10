from pydantic import BaseModel, Field

from backend.app.domain.chat.value_objects.types import ChatTemplate


class Attachment(BaseModel):
    key: str
    file_name: str
    file_type: str
    file_size: float


class ParsedAttachment(BaseModel):
    key: str
    file_name: str
    file_type: str
    file_size: float
    transcript: str = Field(..., max_length=5000)


class GeneratedTechnicalTask(BaseModel):
    version: int
    name: str
    technical_task_template: ChatTemplate
    # content: Any # в будущем будет отдаваться точная pydantic-схема, но пока что считай просто строка

