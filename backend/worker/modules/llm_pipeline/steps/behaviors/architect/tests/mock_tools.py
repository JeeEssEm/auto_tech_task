from __future__ import annotations

from dataclasses import dataclass

from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.context import (
    ArchitectContext,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import (
    ConsistencyCheckResult,
    ContextDetail,
    SourceChunk,
    WrittenSection,
)


@dataclass
class ToolCallRecord:
    tool_name: str
    args: dict


class MockArchitectTools(ArchitectContext):
    """Deterministic mocked tools backend for Architect e2e tests."""

    def __init__(self) -> None:
        self.calls: list[ToolCallRecord] = []
        self._action_index = 0

        self._details: dict[str, ContextDetail] = {
            "db_engine_main": ContextDetail(
                topic_id="db_engine_main",
                winning_value="ClickHouse",
                rationale=(
                    "Выбран для аналитической нагрузки и тяжелых агрегаций; "
                    "PostgreSQL оставлен для транзакционных сценариев."
                ),
                evidence=[
                    {
                        "quote": "Нам нужны быстрые OLAP-отчеты по большим данным.",
                        "author": "Мария",
                        "timestamp": "2026-03-18T10:04:00Z",
                        "source_id": "chat-102",
                    },
                    {
                        "quote": "Postgres годится для OLTP, но аналитика уходит в ClickHouse.",
                        "author": "Алексей",
                        "timestamp": "2026-03-18T10:06:00Z",
                        "source_id": "decision-log-7",
                    },
                ],
                rejected_alternatives=[
                    {
                        "value": "PostgreSQL",
                        "rationale": "Не выбран как основной движок для аналитики.",
                    }
                ],
            ),
            "backend_framework": ContextDetail(
                topic_id="backend_framework",
                winning_value="FastAPI",
                rationale="Async-first API, высокая скорость разработки, строгие pydantic-схемы.",
                evidence=[
                    {
                        "quote": "Берем FastAPI для быстрого MVP и контрактного API.",
                        "author": "Иван",
                        "timestamp": "2026-03-17T09:10:00Z",
                        "source_id": "chat-11",
                    }
                ],
                rejected_alternatives=[
                    {
                        "value": "Django",
                        "rationale": "Избыточен для API-first сценария.",
                    }
                ],
            ),
            "auth_method": ContextDetail(
                topic_id="auth_method",
                winning_value="JWT access + refresh",
                rationale="Сбалансированы безопасность и UX для SPA-клиента.",
                evidence=[
                    {
                        "quote": "Access 15 минут, refresh 14 дней.",
                        "author": "Сергей",
                        "timestamp": "2026-03-17T12:25:00Z",
                        "source_id": "chat-33",
                    }
                ],
                rejected_alternatives=[],
            ),
        }

        self._raw_chunks: list[SourceChunk] = [
            SourceChunk(
                source_id="chat-102",
                source_name="telegram_chat",
                chunk_index=15,
                text=(
                    "Выбор БД: ClickHouse под аналитические запросы, "
                    "PostgreSQL только для транзакционной части."
                ),
                score=0.91,
            ),
            SourceChunk(
                source_id="tz-v1",
                source_name="Bolshoe TZ.md",
                chunk_index=4,
                text="Backend: FastAPI, Redis для кэша и очередей, pydantic DTO.",
                score=0.86,
            ),
            SourceChunk(
                source_id="chat-33",
                source_name="telegram_chat",
                chunk_index=9,
                text="Auth подтвержден: JWT access token + refresh token.",
                score=0.84,
            ),
        ]

    async def get_context_details(self, topic_id: str) -> ContextDetail | None:
        self.calls.append(ToolCallRecord(tool_name="get_context_details", args={"topic_id": topic_id}))
        return self._details.get(topic_id)

    async def search_raw_sources(self, query: str, limit: int = 2) -> list[SourceChunk]:
        self.calls.append(ToolCallRecord(tool_name="search_raw_sources", args={"query": query, "limit": limit}))
        q = query.lower()

        ranked: list[tuple[float, SourceChunk]] = []
        for chunk in self._raw_chunks:
            text = chunk.text.lower()
            token_hits = sum(1 for token in q.split() if token and token in text)
            if token_hits == 0:
                continue
            ranked.append((chunk.score + token_hits * 0.02, chunk))

        ranked.sort(key=lambda it: it[0], reverse=True)
        return [row for _, row in ranked[:limit]]

    async def ask_user(self, question: str, options: list[str] | None) -> str:
        self.calls.append(ToolCallRecord(tool_name="ask_user", args={"question": question, "options": options}))
        self._action_index += 1
        return f"pending-action-{self._action_index:03d}"

    async def validate_consistency(
        self,
        draft_text: str,
        written_sections: list[WrittenSection],
    ) -> ConsistencyCheckResult:
        self.calls.append(
            ToolCallRecord(
                tool_name="validate_consistency",
                args={"draft_text": draft_text, "written_sections_count": len(written_sections)},
            )
        )

        draft_lc = draft_text.lower()
        written_lc = "\n".join(s.content_md for s in written_sections).lower()

        if "ruby" in draft_lc and "fastapi" in written_lc:
            return ConsistencyCheckResult(
                status="CONFLICT",
                reason="Во введении зафиксирован FastAPI, а в секции указан Ruby.",
            )

        return ConsistencyCheckResult(status="OK", reason="")
