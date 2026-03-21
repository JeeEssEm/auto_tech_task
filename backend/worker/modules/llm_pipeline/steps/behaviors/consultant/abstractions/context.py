from abc import ABC, abstractmethod

from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.schemas import (
    GKGSearchResult, GKGNodeDetail,
    SourceChunk
)


class ConsultantContext(ABC):
    """
    Абстракция над хранилищем знаний для Консультанта.
    Реализация будет инжектировать реальные SQL/векторные запросы к Postgres.
    В тестах — мок с фиксированными ответами.
    """

    @abstractmethod
    async def search_gkg(
        self,
        query: str,
        limit: int = 5,
    ) -> list[GKGSearchResult]:
        """Семантический поиск по gkg_nodes WHERE status != 'ARCHIVED'."""
        ...

    @abstractmethod
    async def get_gkg_node_detail(
        self,
        topic_id: str,
    ) -> GKGNodeDetail | None:
        """
        SELECT * FROM gkg_nodes WHERE id = topic_id
        + JOIN gkg_edges для rejected alternatives.
        """
        ...

    @abstractmethod
    async def search_raw_sources(
        self,
        query: str,
        limit: int = 3,
    ) -> list[SourceChunk]:
        """Векторный поиск по таблице исходных чанков (не GKG)."""
        ...
