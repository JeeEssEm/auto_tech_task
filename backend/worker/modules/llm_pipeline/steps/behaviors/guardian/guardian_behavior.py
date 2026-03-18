from pydantic import BaseModel

from backend.worker.modules.llm_pipeline.abstractions.ports import LLMChatPort
from backend.worker.modules.llm_pipeline.steps.behaviors.guardian.prompting import (
    build_guardian_system_prompt,
    build_guardian_user_prompt
)
from backend.worker.modules.llm_pipeline.steps.intent_router.config import IntentRouterSettings
from backend.worker.modules.llm_pipeline.steps.shared.behaviours import BehaviorReason


class GuardianResponse(BaseModel):
    message: str


class GuardianBehavior:
    def __init__(self, chat_port: LLMChatPort, settings: IntentRouterSettings):
        self._chat = chat_port
        self._settings = settings

    async def run(self, reason: BehaviorReason, offending_input: str, project_name: str, project_type: str) -> GuardianResponse:
        system_prompt = build_guardian_system_prompt(project_name, project_type)
        user_prompt = build_guardian_user_prompt(reason, offending_input)

        return await self._chat.chat(
            model=self._settings.model,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_model=GuardianResponse,
        )
