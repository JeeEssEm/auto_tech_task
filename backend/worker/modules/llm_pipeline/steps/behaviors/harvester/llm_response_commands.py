from pydantic import BaseModel, Field

from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.active_working_memory.schemas import Evidence, AWMStatus


class ResolveCommand(BaseModel):
    topic_id: str
    final_value: str
    evidence: Evidence


class UpdateCommand(BaseModel):
    topic_id: str
    new_status: AWMStatus
    new_value: str | None = None
    new_question: str | None = None
    evidence: Evidence


class CreateCommand(BaseModel):
    scope: str
    property: str
    value: str
    status: AWMStatus = AWMStatus.PROPOSED
    evidence: Evidence


class HarvesterLLMOutput(BaseModel):
    resolve: list[ResolveCommand] = Field(default_factory=list)
    update: list[UpdateCommand] = Field(default_factory=list)
    create: list[CreateCommand] = Field(default_factory=list)
    has_remaining_facts: bool = False  # self-correction loop
