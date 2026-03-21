import json
import time
from typing import Any, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from backend.worker.modules.llm_pipeline.abstractions.ports import LLMChatPort
from backend.worker.modules.llm_pipeline.providers.schemas import ChatResult
from backend.worker.modules.llm_pipeline.providers.configs.openai_settings import OpenAIChatSettings
from backend.worker.modules.llm_pipeline.providers.utils.json_utils import (
    escape_control_chars_in_strings,
    extract_first_json_object
)
from backend.worker.modules.llm_pipeline.providers.utils.logs import build_file_logger
from backend.worker.modules.llm_pipeline.providers.utils.retries import is_retryable

ResponseT = TypeVar('ResponseT', bound=BaseModel | str)


class OpenAIChatAdapter(LLMChatPort):
    """
    Реализация LLMChatPort для любого OpenAI-совместимого эндпоинта.

    Особенности:
    - ретраи через tenacity (exponential backoff, только retryable HTTP-коды)
    - всё логируется в файл: запрос, ответ, tokens, latency, event_id
    - в консоль ничего не пишется
    """

    def __init__(self, settings: OpenAIChatSettings) -> None:
        self.settings = settings
        self._log = build_file_logger(__name__, settings.log_path)
        self._timeout = httpx.Timeout(settings.timeout_seconds)

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_model: Type[ResponseT],
        event_id: str | None = None,
    ) -> ResponseT:
        """Chat with LLM and parse response into Pydantic model with automatic retries on invalid JSON/schema."""
        payload = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"

        self._log.debug(
            "→ request | event=%s model=%s response_model=%s messages=%s",
            event_id, model, response_model.__name__, json.dumps(messages, ensure_ascii=False),
        )

        call = retry(
            retry=retry_if_exception(is_retryable),
            stop=stop_after_attempt(self.settings.max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=16),
            reraise=True,
        )(self._call_once)

        return await call(
            url=f"{self.settings.base_url}/chat/completions",
            headers=headers,
            payload=payload,
            event_id=event_id,
            model=model,
            response_model=response_model,
        )

    async def _call_once(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        event_id: str | None,
        model: str,
        response_model: Type[ResponseT],
    ) -> ResponseT:
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, headers=headers, json=payload)

        latency_ms = int((time.perf_counter() - started) * 1000)
        response.raise_for_status()

        body = response.json()
        choices = body.get("choices") or []
        if not choices:
            raise ValueError("Empty choices in provider response")

        content: str = choices[0]["message"]["content"] or ""
        usage: dict[str, int] = body.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        actual_model = body.get("model") or model

        self._log.debug(
            "← response | event=%s model=%s latency_ms=%d "
            "prompt_tokens=%d completion_tokens=%d",
            event_id, actual_model, latency_ms,
            prompt_tokens, completion_tokens,
        )

        # Parse and validate response into schema
        try:
            parsed = self._parse_json_response(content, response_model)
            self._log.debug(
                "✓ schema_parse success | event=%s model=%s schema=%s",
                event_id, actual_model, response_model.__name__,
            )
            return parsed
        except (json.JSONDecodeError, ValidationError) as e:
            self._log.warning(
                "✗ schema_parse failed | event=%s model=%s schema=%s error=%s raw_content=%s",
                event_id, actual_model, response_model.__name__, str(e), content[:500],
            )
            # Mark as retryable - tenacity will retry the entire call
            raise ValueError(
                f"Invalid JSON/schema from LLM (retryable). Error: {str(e)}"
            ) from e

    def _parse_json_response(self, content: str, response_model: Type[ResponseT]) -> ResponseT:
        """Extract JSON from content and validate against Pydantic model."""
        # Clean up markdown code blocks
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        if response_model is str:
            return content

        content = extract_first_json_object(content.strip())
        content = escape_control_chars_in_strings(content)
        return response_model.model_validate_json(content)
