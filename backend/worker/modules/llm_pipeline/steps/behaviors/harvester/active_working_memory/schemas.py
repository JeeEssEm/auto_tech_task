from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class AWMStatus(StrEnum):
    PROPOSED = "PROPOSED"
    DISCUSSING = "DISCUSSING"
    STALE = "STALE"
    RESOLVED = "RESOLVED"


class Evidence(BaseModel):
    chunk_index: int
    quote: str
    author: str | None = None
    timestamp: str | None = None  # для видео/аудио


class AWMTopic(BaseModel):
    topic_id: str = Field(default_factory=lambda: str(uuid4()))
    status: AWMStatus = AWMStatus.PROPOSED
    scope: str
    property: str
    current_value: str
    participants: list[str] = Field(default_factory=list)
    last_updated_chunk: int
    unresolved_questions: list[str] = Field(default_factory=list)
    evidence_backlog: list[Evidence] = Field(default_factory=list)


class AWMState(BaseModel):
    active_topics: list[AWMTopic] = Field(default_factory=list)
