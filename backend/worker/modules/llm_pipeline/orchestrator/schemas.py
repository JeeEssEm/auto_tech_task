from dataclasses import dataclass

from backend.worker.modules.llm_pipeline.orchestrator.state import OrchestratorState
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import ArchitectResponse
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.schemas import PendingConflict


@dataclass
class OrchestratorResult:
    chat_text: str
    doc_updates: list[ArchitectResponse]
    pending_conflicts: list[PendingConflict]

    @classmethod
    def from_state(cls, state: OrchestratorState) -> "OrchestratorResult":
        return cls(
            chat_text="\n\n".join(state.get("chat_parts", []) or ["Принято."]),
            doc_updates=state.get("architect_responses", []),
            pending_conflicts=state.get("pending_conflicts", []),
        )
