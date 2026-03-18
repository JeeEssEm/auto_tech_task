from enum import StrEnum

from pydantic import BaseModel, Field

from backend.worker.modules.llm_pipeline.steps.intent_router.behaviours import RouterBehavior


class AttachmentInfo(BaseModel):
    file_name: str
    file_size_kilobytes: int
    truncated_content: str | None    # урезать до первых 50 символов


class IntentRouterRequest(BaseModel):
    user_prompt: str
    attachments: list[AttachmentInfo]


class IntentRouterResponse(BaseModel):
    behaviors: list[RouterBehavior]
