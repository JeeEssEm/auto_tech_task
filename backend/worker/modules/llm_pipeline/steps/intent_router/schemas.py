from pydantic import BaseModel, Field

from backend.worker.modules.llm_pipeline.steps.shared.behaviours import RouterBehavior


class AttachmentInfo(BaseModel):
    file_name: str
    file_size_kilobytes: int
    truncated_content: str | None    # урезать до первых 50 символов


class IntentRouterRequest(BaseModel):
    user_prompt: str
    attachments: list[AttachmentInfo]
    pending_actions: list[str] = Field(default_factory=lambda: []) # TODO: добавить
    gkg_snapshot: str | None = None # TODO: добавить
    doc_snapshot: str | None = None # структура документа ТЗ TODO: добавить
    last_user_actions: list[str] = Field(default_factory=lambda: []) # TODO: добавить


class IntentRouterResponse(BaseModel):
    behaviors: list[RouterBehavior]
