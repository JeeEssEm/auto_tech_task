from __future__ import annotations

from dataclasses import dataclass

from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.context import (
    ConsultantContext,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.schemas import (
    GKGNodeDetail,
    GKGSearchResult,
    SourceChunk,
)


@dataclass
class ToolCallRecord:
    tool_name: str
    args: dict


class MockConsultantTools(ConsultantContext):
    """Mocked consultant tools for real e2e runs with deterministic project data."""

    def __init__(self) -> None:
        self.calls: list[ToolCallRecord] = []

        self._gkg_nodes: list[GKGSearchResult] = [
            GKGSearchResult(
                topic_id="db_engine_main",
                scope="База данных",
                property="Движок",
                value="ClickHouse",
                status="RESOLVED",
                rationale="Выбран для аналитических OLAP-запросов и дешевого масштабирования чтения.",
                source_ids=["chat-102", "decision-log-7"],
                score=0.95,
            ),
            GKGSearchResult(
                topic_id="backend_framework",
                scope="Бэкенд",
                property="Фреймворк",
                value="FastAPI",
                status="RESOLVED",
                rationale="Нужны асинхронность, Pydantic-схемы и высокая скорость разработки API.",
                source_ids=["chat-11", "tz-v1"],
                score=0.88,
            ),
            GKGSearchResult(
                topic_id="auth_method",
                scope="API",
                property="Аутентификация",
                value="JWT access + refresh",
                status="NO_CONFLICT",
                rationale="Подходит для SPA и изоляции коротких/длинных сессий.",
                source_ids=["chat-33"],
                score=0.84,
            ),
        ]

        self._details: dict[str, GKGNodeDetail] = {
            "db_engine_main": GKGNodeDetail(
                topic_id="db_engine_main",
                scope="База данных",
                property="Движок",
                winning_value="ClickHouse",
                rationale=(
                    "Приоритет аналитических нагрузок и сложных агрегаций; "
                    "Postgres признан менее подходящим для целевого профиля OLAP."
                ),
                evidence=[
                    {
                        "quote": "Нам важны быстрые аналитические отчеты по большим объемам.",
                        "author": "Мария",
                        "timestamp": "2026-03-18T10:04:00Z",
                        "source_id": "chat-102",
                    },
                    {
                        "quote": "Postgres оставляем для транзакционной части, но не как главный аналитический движок.",
                        "author": "Алексей",
                        "timestamp": "2026-03-18T10:06:00Z",
                        "source_id": "decision-log-7",
                    },
                ],
                rejected_alternatives=[
                    {
                        "value": "PostgreSQL",
                        "rationale": "Не оптимален как основной движок для тяжелой OLAP-аналитики.",
                    }
                ],
            ),
            "backend_framework": GKGNodeDetail(
                topic_id="backend_framework",
                scope="Бэкенд",
                property="Фреймворк",
                winning_value="FastAPI",
                rationale="Нужна async-first архитектура и простая валидация DTO.",
                evidence=[
                    {
                        "quote": "Берем FastAPI: быстрее выдадим MVP и упростим схему API.",
                        "author": "Иван",
                        "timestamp": "2026-03-17T09:10:00Z",
                        "source_id": "chat-11",
                    }
                ],
                rejected_alternatives=[
                    {
                        "value": "Django",
                        "rationale": "Слишком тяжело для текущего API-first контура.",
                    }
                ],
            ),
            "auth_method": GKGNodeDetail(
                topic_id="auth_method",
                scope="API",
                property="Аутентификация",
                winning_value="JWT access + refresh",
                rationale="Баланс безопасности и UX для SPA и мобильного клиента.",
                evidence=[
                    {
                        "quote": "Короткий access, длинный refresh через отдельный endpoint.",
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
                    "Обсуждали выбор базы данных для аналитики. "
                    "Мария предложила ClickHouse как основной OLAP-движок. "
                    "PostgreSQL решили оставить только для транзакционных операций."
                ),
                score=0.91,
            ),
            SourceChunk(
                source_id="tz-v1",
                source_name="Большое ТЗ.md",
                chunk_index=4,
                text=(
                    "Backend: FastAPI, асинхронные обработчики, Redis для кэша и брокера событий."
                ),
                score=0.86,
            ),
            SourceChunk(
                source_id="chat-33",
                source_name="telegram_chat",
                chunk_index=9,
                text=(
                    "Для авторизации подтвержден подход JWT: access token 15 минут, "
                    "refresh token 14 дней."
                ),
                score=0.84,
            ),
        ]

    async def search_gkg(self, query: str, limit: int = 5) -> list[GKGSearchResult]:
        self.calls.append(ToolCallRecord(tool_name="search_gkg", args={"query": query, "limit": limit}))
        q = query.lower()

        ranked: list[tuple[float, GKGSearchResult]] = []
        for node in self._gkg_nodes:
            text = " ".join([node.scope, node.property, node.value, node.rationale]).lower()
            token_hits = sum(1 for token in q.split() if token and token in text)
            score = node.score + token_hits * 0.02
            if token_hits > 0 or any(k in q for k in ("база", "fastapi", "jwt", "clickhouse", "postgres")):
                ranked.append((score, node))

        ranked.sort(key=lambda it: it[0], reverse=True)
        return [row for _, row in ranked[:limit]]

    async def get_gkg_node_detail(self, topic_id: str) -> GKGNodeDetail | None:
        self.calls.append(ToolCallRecord(tool_name="get_gkg_node_detail", args={"topic_id": topic_id}))
        return self._details.get(topic_id)

    async def search_raw_sources(self, query: str, limit: int = 3) -> list[SourceChunk]:
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
