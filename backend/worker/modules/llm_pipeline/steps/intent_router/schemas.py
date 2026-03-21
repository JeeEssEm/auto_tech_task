from pydantic import BaseModel, Field

from backend.worker.modules.llm_pipeline.steps.shared.behaviours import RouterBehavior


class AttachmentInfo(BaseModel):
    file_name: str
    truncated_content: str


class IntentRouterRequest(BaseModel):
    user_prompt: str
    attachments: list[AttachmentInfo]
    pending_actions: list[str] = Field(default_factory=list)
    gkg_snapshot: str | None = None
    doc_snapshot: str | None = None


class IntentRouterResponse(BaseModel):
    behaviors: list[RouterBehavior]
