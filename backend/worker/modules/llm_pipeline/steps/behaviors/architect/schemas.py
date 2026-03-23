"""
schemas.py — типы ответов LLM и публичный результат ArchitectBehavior.
"""

from typing import Literal, Annotated, Union

from pydantic import BaseModel, Field


class GKGFact(BaseModel):
    """Краткий факт из GKG — попадает в [SECTION FACTS] промпта."""
    topic_id: str
    scope: str
    property: str
    value: str
    status: str       # NO_CONFLICT | RESOLVED | UNRESOLVED
    source_ids: list[str]


class ContextDetail(BaseModel):
    """Полное досье по одному узлу GKG — результат get_context_details."""
    topic_id: str
    winning_value: str
    rationale: str
    evidence: list[dict]              # [{quote, author, timestamp, source_id}]
    rejected_alternatives: list[dict] # [{value, rationale}]


class SourceChunk(BaseModel):
    """Фрагмент исходного документа — результат search_raw_sources."""
    source_id: str
    source_name: str   # имя файла / "telegram_chat" / "call_2026-03-18"
    chunk_index: int
    text: str
    score: float


class ConsistencyCheckResult(BaseModel):
    """Результат validate_consistency."""
    status: str        # OK | CONFLICT
    reason: str = ""   # заполнено только при CONFLICT


class WrittenSection(BaseModel):
    """Уже написанная секция документа — идёт в [ALREADY WRITTEN SECTIONS]."""
    section_id: str
    title: str
    content_md: str    # обрезается в промпте до 300 символов, полный текст здесь


class PendingAction(BaseModel):
    """Вопрос пользователю, созданный через ask_user."""
    action_id: str
    question: str
    options: list[str] | None = None


class ToolCallOutput(BaseModel):
    is_final: Literal[False] = False
    tool_name: Literal[
        "search_gkg",
        "get_context_details",
        "search_raw_sources",
        "ask_user",
        "validate_consistency",
    ]
    tool_args: dict
    reasoning: str   # chain-of-thought: зачем вызываем


class SectionOutput(BaseModel):
    """Финальный результат работы Архитектора над одной секцией."""
    is_final: Literal[True] = True
    section_id: str
    content_md: str
    status: Literal["generated", "partial", "missing"]
    pending_actions: list[PendingAction] = Field(default_factory=list)


ArchitectLLMOutput = Annotated[
    Union[ToolCallOutput, SectionOutput],
    Field(discriminator="is_final"),
]


class ArchitectResponse(BaseModel):
    section_id: str
    content_md: str
    status: Literal["generated", "partial", "missing"]
    pending_actions: list[PendingAction]
    used_tool_calls: int
    was_truncated: bool = False
