from pydantic import BaseModel


class StagingNode(BaseModel):
    source_id: str
    scope: str
    property: str
    value: str
    content_raw: str       # дословная цитата
    author: str | None
    timestamp: str | None
    chunk_index: int
