from enum import StrEnum

from pydantic import Field, BaseModel


class BehaviorRole(StrEnum):
    HARVESTER = "Harvester"
    ARCHITECT = "Architect"
    CONSULTANT = "Consultant"
    INTERROGATOR = "Interrogator"
    GUARDIAN = "Guardian"


class BehaviorReason(StrEnum):
    NEW_FACT_DETECTED = "new_fact_detected"
    OFFTOPIC_SEGMENT = "offtopic_segment"
    QUESTION_ABOUT_PROJECT = "question_about_project"
    MISSING_REQUIRED_DATA = "missing_required_data"
    CONFLICT_DETECTED = "conflict_detected"
    TECHNICAL_ROUTING = "technical_routing"
    SPEC_BLOCK_AFFECTED = "spec_block_affected"
    DEFAULT_SAFE_ROUTE = "default_safe_route"


class RouterBehavior(BaseModel):
    role: BehaviorRole
    reason: BehaviorReason
    user_prompt: str = Field(validation_alias="quote")
