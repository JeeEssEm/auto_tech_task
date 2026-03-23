"""
architect_context.py

Два независимых куска:

1. Схемы данных — то, чем оперирует Архитектор (факты из GKG, детали узлов,
   результаты проверки и т.д.).

2. ArchitectContext (ABC) — абстракция над хранилищем. Реализация инжектирует
   реальные SQL/векторные запросы к Postgres. В тестах — мок.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from pydantic import BaseModel

from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import (
    ContextDetail, SourceChunk,
    ConsistencyCheckResult, WrittenSection
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.schemas import GKGSearchResult


class ArchitectContext(ABC):
    """
    Абстракция над хранилищем знаний для Архитектора.

    Четыре метода = четыре инструмента агента.
    Реализация делает SQL/векторные запросы к Postgres (pgvector).
    В тестах — MockArchitectContext с фиксированными ответами.
    """

    @abstractmethod
    async def search_gkg(
            self,
            query: str,
            limit: int = 10,
    ) -> list[GKGSearchResult]:
        """
        Семантический поиск по gkg_nodes WHERE status != 'ARCHIVED'.
        Используется в фазе написания секции.
        """
        ...

    @abstractmethod
    async def get_context_details(
        self,
        topic_id: str,
    ) -> ContextDetail | None:
        """
        SELECT * FROM gkg_nodes WHERE id = topic_id
        + LEFT JOIN gkg_edges → собрать rejected_alternatives из ARCHIVED-нод
        """
        ...

    @abstractmethod
    async def search_raw_sources(
        self,
        query: str,
        limit: int = 2,
    ) -> list[SourceChunk]:
        """
        Векторный поиск по таблице исходных чанков (не gkg_nodes).
        Возвращает raw-текст без интерпретации.
        """
        ...

    @abstractmethod
    async def ask_user(
        self,
        question: str,
        options: list[str] | None,
    ) -> str:
        """
        Создаёт запись в таблице pending_actions со статусом WAITING.
        Возвращает action_id.
        Приостановка генерации — на уровне caller'а, не здесь.
        """
        ...

    @abstractmethod
    async def validate_consistency(
        self,
        draft_text: str,
        written_sections: list[WrittenSection],
    ) -> ConsistencyCheckResult:
        """
        Отправляет draft_text + резюме written_sections быстрой модели
        (GPT-4o-mini / Haiku) с задачей найти логические противоречия.
        """
        ...
