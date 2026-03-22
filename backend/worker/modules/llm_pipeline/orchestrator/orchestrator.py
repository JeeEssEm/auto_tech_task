import asyncio

from backend.worker.modules.llm_pipeline.orchestrator.graph_builder import build_graph
from backend.worker.modules.llm_pipeline.orchestrator.nodes import OrchestratorDeps
from backend.worker.modules.llm_pipeline.orchestrator.schemas import OrchestratorResult
from backend.worker.modules.llm_pipeline.orchestrator.state import OrchestratorState, Attachment


class Orchestrator:
    """
    Тонкая обёртка над скомпилированным графом.
    Используется в API-обработчике /chat/message.

    Пример:
        orchestrator = Orchestrator(deps)
        result = await orchestrator.run(project_id=42, user_input="текст")
        # result.chat_text  — текст для чата
        # result.doc_updates — обновлённые секции ТЗ
        # result.pending_conflicts — конфликты для UI
    """

    def __init__(self, deps: OrchestratorDeps) -> None:
        self._graph = build_graph(deps)
        self._deps = deps

    async def run(self, project_id: int, user_input: str, attachments: list[Attachment]) -> "OrchestratorResult":
        gkg_snapshot, doc_snapshot, pending_actions = await asyncio.gather(
            self._deps.get_gkg_snapshot(project_id),
            self._deps.get_doc_snapshot(project_id),
            self._deps.get_pending_actions(project_id),
        )

        initial_state: OrchestratorState = {
            "project_id": project_id,
            "user_input": user_input,
            "behaviors": [],
            "guardian_messages": [],
            "consultant_responses": [],
            "harvested_nodes": [],
            "gkg_nodes": [],
            "pending_conflicts": [],
            "architect_responses": [],
            "chat_parts": [],
            "attachments": attachments,
            "gkg_snapshot": gkg_snapshot,
            "doc_snapshot": doc_snapshot,
            "pending_actions": pending_actions,
        }
        final_state: OrchestratorState = await self._graph.ainvoke(initial_state)

        return OrchestratorResult.from_state(final_state)
