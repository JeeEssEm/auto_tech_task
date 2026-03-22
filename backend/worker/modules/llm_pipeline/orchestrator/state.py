import operator
from typing import Annotated

from typing_extensions import TypedDict

from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.schemas import DocumentSnapshot
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import ArchitectResponse
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.schemas import ConsultantResponse
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.schemas import (
    GKGNode,
    PendingConflict,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.staging import StagingNode
from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import AttachmentInfo
from backend.worker.modules.llm_pipeline.steps.shared.behaviours import RouterBehavior


class Attachment(TypedDict):
    source_id: str
    text: str
    name: str


class OrchestratorState(TypedDict):
    project_id: int
    user_input: str
    attachments: list[Attachment]

    behaviors: list[RouterBehavior]

    guardian_messages: Annotated[list[str], operator.add]
    consultant_responses: Annotated[list[ConsultantResponse], operator.add]
    harvested_nodes: Annotated[list[StagingNode], operator.add]

    gkg_nodes: Annotated[list[GKGNode], operator.add]
    pending_conflicts: Annotated[list[PendingConflict], operator.add]

    architect_responses: Annotated[list[ArchitectResponse], operator.add]

    chat_parts: Annotated[list[str], operator.add]

    gkg_snapshot: str
    doc_snapshot: str
    pending_actions: list[str]


class ArchitectNodeInput(TypedDict):
    project_id: int
    section_snapshot: DocumentSnapshot


class GuardianNodeInput(TypedDict):
    project_id: int
    guardian_behavior: RouterBehavior
