from pydantic import BaseModel


class Attachment(BaseModel):
    key: str
    file_name: str
    file_type: str
    file_size: float
