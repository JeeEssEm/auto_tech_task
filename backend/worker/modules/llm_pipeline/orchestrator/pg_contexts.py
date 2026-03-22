from __future__ import annotations

from contextvars import ContextVar

from backend.app.infrastructure.persistent.llm_pipeline import GKGRepository, PendingActionsRepository
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.context import ArchitectContext
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import (
    ConsistencyCheckResult,
    ContextDetail,
    SourceChunk as ArchitectSourceChunk,
    WrittenSection,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.context import ConsultantContext
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.schemas import (
    GKGNodeDetail,
    GKGSearchResult,
    SourceChunk as ConsultantSourceChunk,
)


class PgConsultantContext(ConsultantContext):
    def __init__(self, gkg_repo: GKGRepository) -> None:
        self._gkg_repo = gkg_repo
        self._project_id_var: ContextVar[int] = ContextVar("consultant_project_id", default=1)

    def set_project_id(self, project_id: int) -> None:
        self._project_id_var.set(project_id)

    def _project_id(self) -> int:
        return self._project_id_var.get()

    async def search_gkg(self, query: str, limit: int = 5) -> list[GKGSearchResult]:
        return await self._gkg_repo.consultant_search_gkg(self._project_id(), query, limit)

    async def get_gkg_node_detail(self, topic_id: str) -> GKGNodeDetail | None:
        return await self._gkg_repo.consultant_get_gkg_node_detail(self._project_id(), topic_id)

    async def search_raw_sources(self, query: str, limit: int = 3) -> list[ConsultantSourceChunk]:
        return await self._gkg_repo.consultant_search_raw_sources(self._project_id(), query, limit)


class PgArchitectContext(ArchitectContext):
    def __init__(self, gkg_repo: GKGRepository, pending_repo: PendingActionsRepository) -> None:
        self._gkg_repo = gkg_repo
        self._pending_repo = pending_repo
        self._project_id_var: ContextVar[int] = ContextVar("architect_project_id", default=1)

    def set_project_id(self, project_id: int) -> None:
        self._project_id_var.set(project_id)

    def _project_id(self) -> int:
        return self._project_id_var.get()

    async def get_context_details(self, topic_id: str) -> ContextDetail | None:
        return await self._gkg_repo.architect_get_context_details(self._project_id(), topic_id)

    async def search_raw_sources(self, query: str, limit: int = 2) -> list[ArchitectSourceChunk]:
        return await self._gkg_repo.architect_search_raw_sources(self._project_id(), query, limit)

    async def ask_user(self, question: str, options: list[str] | None) -> str:
        return await self._pending_repo.create_pending_action(self._project_id(), question, options)

    async def validate_consistency(
        self,
        draft_text: str,
        written_sections: list[WrittenSection],
    ) -> ConsistencyCheckResult:
        return await self._gkg_repo.architect_validate_consistency(draft_text, written_sections)
