"""
Pytest fixtures for ArchitectBehavior E2E tests.

These tests use a real LLM adapter and mocked architect tools
(get_context_details, search_raw_sources, ask_user, validate_consistency).
"""

import asyncio
import logging
from typing import Type, TypeVar

import httpx
from pydantic import BaseModel

import pytest

from backend.worker.modules.llm_pipeline.providers.configs.openai_settings import OpenAIChatSettings
from backend.worker.modules.llm_pipeline.providers.openai_adapter import OpenAIChatAdapter
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.architect_behavior import ArchitectBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.config import ArchitectSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.tests.mock_tools import MockArchitectTools


ResponseT = TypeVar("ResponseT", bound=BaseModel)


class OpenAICompatChatAdapter:
    """
    Compatibility adapter for ArchitectBehavior.

    Architect now requests response_model=str, while OpenAIChatAdapter expects a
    Pydantic response model. This wrapper keeps real LLM calls and supports both:
    - str: returns raw assistant content
    - BaseModel: delegates to OpenAIChatAdapter
    """

    def __init__(self, settings: OpenAIChatSettings):
        self._settings = settings
        self._typed_adapter = OpenAIChatAdapter(settings)
        self._timeout = httpx.Timeout(settings.timeout_seconds)

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_model: Type[ResponseT] | type[str],
        event_id: str | None = None,
    ):
        if response_model is str:
            headers = {"Content-Type": "application/json"}
            if self._settings.api_key:
                headers["Authorization"] = f"Bearer {self._settings.api_key}"
            if event_id:
                headers["Idempotency-Key"] = event_id

            payload = {
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "messages": messages,
            }

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._settings.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

            response.raise_for_status()
            body = response.json()
            choices = body.get("choices") or []
            if not choices:
                raise ValueError("Empty choices in provider response")

            content = choices[0].get("message", {}).get("content")
            return str(content or "")

        return await self._typed_adapter.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_model=response_model,
            event_id=event_id,
        )


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def architect_settings():
    """Load Architect settings from environment variables."""
    try:
        settings = ArchitectSettings()
        print("\nArchitect settings loaded:")
        print(f"  Provider: {settings.provider}")
        print(f"  Base URL: {settings.base_url}")
        print(f"  Model: {settings.model}")
        print(f"  Max tokens: {settings.max_tokens}")
        print(f"  Max tool calls: {settings.max_tool_calls}")
        print(f"  Max consistency retries: {settings.max_consistency_retries}")
        return settings
    except Exception as e:
        pytest.skip(f"Failed to load Architect settings: {e}")


@pytest.fixture
def llm_chat_adapter(architect_settings):
    """Create compatible real LLM adapter with settings from Architect config."""
    settings = OpenAIChatSettings(
        base_url=architect_settings.base_url,
        api_key=architect_settings.api_key,
        temperature=architect_settings.temperature,
        max_tokens=architect_settings.max_tokens,
        timeout_seconds=architect_settings.timeout_seconds,
        max_attempts=3,
        log_path="architect_test.log",
    )
    adapter = OpenAICompatChatAdapter(settings)
    print(f"\nOpenAIChatAdapter initialized with {settings.base_url}")
    return adapter


@pytest.fixture
def mock_architect_tools():
    """Mocked tools backend for architect agent loop."""
    return MockArchitectTools()


@pytest.fixture
def architect_behavior(llm_chat_adapter, mock_architect_tools, architect_settings):
    """Create ArchitectBehavior with real LLM and mocked tools."""
    return ArchitectBehavior(
        chat_port=llm_chat_adapter,
        context=mock_architect_tools,
        settings=architect_settings,
    )


@pytest.fixture(autouse=True)
def configure_logging():
    """Setup logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("architect_test.log")],
    )


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end (requires real LLM)")
    config.addinivalue_line("markers", "slow: marks tests as slow (multiple tool rounds + LLM)")
