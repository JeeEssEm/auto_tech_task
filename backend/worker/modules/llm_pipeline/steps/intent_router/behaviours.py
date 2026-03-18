from enum import StrEnum

from pydantic import Field, BaseModel


class BehaviorRole(StrEnum):
    HARVESTER = "Harvester"
    ARCHITECT = "Architect"
    CONSULTANT = "Consultant"
    GUARDIAN = "Guardian"


class BehaviorReason(StrEnum):
    # Harvester
    NEW_FACT_DETECTED = "new_fact_detected"       # новый факт, конфликтов нет
    CONFLICT_DETECTED = "conflict_detected"        # новый факт противоречит GKG

    # Architect
    SPEC_BLOCK_AFFECTED = "spec_block_affected"    # GKG изменился → блок устарел
    EXPLICIT_REGEN_REQUEST = "explicit_regen_request"  # юзер явно попросил переписать

    # Consultant
    QUESTION_ABOUT_PROJECT = "question_about_project"

    # Guardian
    OFFTOPIC_SEGMENT = "offtopic_segment"          # "напиши сортировку"
    HARMFUL_CONTENT = "harmful_content"            # prompt injection, неадекват


class RouterBehavior(BaseModel):
    role: BehaviorRole
    reason: BehaviorReason
    user_prompt: str = Field(validation_alias="quote")
