from backend.worker.modules.llm_pipeline.abstractions.ports import LLMChatPort
from backend.worker.modules.llm_pipeline.steps.intent_router.config import IntentRouterSettings
from backend.worker.modules.llm_pipeline.steps.intent_router.prompting import build_system_prompt, build_user_prompt
from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import IntentRouterRequest, IntentRouterResponse

_SYSTEM_PROMPT = build_system_prompt()


class IntentRouter:
    def __init__(self, chat_port: LLMChatPort, settings: IntentRouterSettings):
        self._chat_port = chat_port
        self._settings = settings

    async def extract_behaviours(self, request: IntentRouterRequest):
        return await self._chat_port.chat(
            model=self._settings.model,
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(request)},
            ],
            response_model=IntentRouterResponse,
        )
