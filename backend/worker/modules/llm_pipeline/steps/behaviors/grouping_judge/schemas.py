from typing import Literal
from uuid import uuid4

from pydantic import BaseModel
from enum import Enum

from backend.worker.modules.llm_pipeline.steps.embedder.schemas import EmbeddedStagingNode


class ConflictStatus(str, Enum):
    NO_CONFLICT = "NO_CONFLICT"
    RESOLVED = "RESOLVED"      # судья выбрал победителя
    UNRESOLVED = "UNRESOLVED"  # нужен пользователь


class ClusterVerdict(BaseModel):
    """Что судья решил про один кластер (или подтему внутри кластера)"""
    scope: str
    property: str
    winning_value: str | None       # None если UNRESOLVED
    status: ConflictStatus
    rationale: str                  # почему выбрал именно это
    discarded_node_indices: list[int]  # мусор внутри кластера
    source_node_indices: list[int]     # какие StagingNode вошли


class GKGNode(BaseModel):
    id: str = ""
    scope: str
    property: str
    value: str
    content_raw: str
    status: Literal["NO_CONFLICT", "RESOLVED", "UNRESOLVED"]
    source_ids: list[str]
    rationale: str
    embedding: list[float]

    def __init__(self, **data):
        if not data.get("id"):
            data["id"] = str(uuid4())
        super().__init__(**data)


class PendingConflict(BaseModel):
    """UNRESOLVED кластер — уходит пользователю как вопрос."""
    id: str = ""
    scope: str
    property: str
    options: list[EmbeddedStagingNode]  # варианты на выбор
    rationale: str  # почему судья не смог выбрать

    def __init__(self, **data):
        if not data.get("id"):
            data["id"] = str(uuid4())
        super().__init__(**data)


class ClusterResult(BaseModel):
    status: Literal["NO_CONFLICT", "DUPLICATE", "RESOLVED", "UNRESOLVED", "SPLIT"]
    winning_node: EmbeddedStagingNode | None = None
    split_nodes: list[EmbeddedStagingNode] | None = None  # SPLIT: каждая → NO_CONFLICT
    conflict_options: list[EmbeddedStagingNode] | None = None  # UNRESOLVED: варианты пользователю
    rationale: str = ""
    all_source_ids: list[str] = []


class JudgeResponse(BaseModel):
    verdict: Literal["RESOLVED", "UNRESOLVED", "SPLIT"]

    winning_index: int | None = None

    # SPLIT: список групп индексов — каждая группа станет отдельным фактом.
    # Пример: [[0, 2], [1, 3]] — две независимые темы внутри кластера.
    split_groups: list[list[int]] | None = None

    rationale: str  # обязательно — используется в GKG и показывается пользователю


class GroupingJudgeResult(BaseModel):
    gkg_nodes: list[GKGNode]
    pending_conflicts: list[PendingConflict]
