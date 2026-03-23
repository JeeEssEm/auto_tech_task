from typing import Literal

from pydantic import BaseModel, Field

from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import ArchitectResponse


class SectionPlan(BaseModel):
    sections_to_write: list[str]
    reasoning: str


class ArchitectCampaignResponse(BaseModel):
    written: list[ArchitectResponse]


class SectionState(BaseModel):
    section_id: str
    title: str
    level: int
    required: bool
    context_hint: str
    content_md: str = ""
    is_manual: bool = False


class ArchitectCampaign(BaseModel):
    user_message: str
    trigger_reason: Literal[
        "initial_generation",
        "spec_block_affected",
        "explicit_regen_request",
    ]
    document: list[SectionState]
    forced_sections: list[str] = Field(default_factory=list)
