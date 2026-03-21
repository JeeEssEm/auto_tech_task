from typing import Literal

from pydantic import BaseModel


class GKGSearchResult(BaseModel):
    topic_id: str
    scope: str
    property: str
    value: str
    status: Literal["NO_CONFLICT", "RESOLVED", "UNRESOLVED"]
    rationale: str       # почему именно это решение
    source_ids: list[str]
    score: float         # семантическая близость к запросу


class GKGNodeDetail(BaseModel):
    topic_id: str
    scope: str
    property: str
    winning_value: str
    rationale: str
    # Полная история: кто предлагал, что отклонили
    evidence: list[dict]        # [{quote, author, timestamp, source_id}]
    rejected_alternatives: list[dict]   # [{value, rationale}]


class SourceChunk(BaseModel):
    source_id: str
    source_name: str    # "protocol_4.pdf", "telegram_chat"
    chunk_index: int
    text: str
    score: float
