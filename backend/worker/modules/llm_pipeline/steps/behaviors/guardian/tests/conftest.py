"""
Pytest configuration and fixtures for GuardianBehavior E2E tests.

These tests call a real LLM via `OpenAIChatAdapter` using the same environment
variables as IntentRouter (see `IntentRouterSettings`).
"""

import asyncio
import logging

import pytest

from backend.worker.modules.llm_pipeline.providers.configs.openai_settings import OpenAIChatSettings
from backend.worker.modules.llm_pipeline.providers.openai_adapter import OpenAIChatAdapter
from backend.worker.modules.llm_pipeline.steps.behaviors.guardian.guardian_behavior import GuardianBehavior
from backend.worker.modules.llm_pipeline.steps.intent_router.config import IntentRouterSettings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def guardian_settings():
    """Load Guardian settings from environment variables (IntentRouterSettings)."""
    try:
        settings = IntentRouterSettings()
        print(f"\n✓ Guardian settings loaded:")
        print(f"  Provider: {settings.provider}")
        print(f"  Base URL: {settings.base_url}")
        print(f"  Model: {settings.model}")
        print(f"  Temperature: {settings.temperature}")
        print(f"  Max tokens: {settings.max_tokens}")
        return settings
    except Exception as e:
        pytest.skip(f"Failed to load Guardian settings: {e}")


@pytest.fixture
def llm_chat_adapter(guardian_settings):
    """Create OpenAIChatAdapter with settings from IntentRouter config."""
    settings = OpenAIChatSettings(
        base_url=guardian_settings.base_url,
        api_key=guardian_settings.api_key,
        temperature=guardian_settings.temperature,
        max_tokens=guardian_settings.max_tokens,
        timeout_seconds=guardian_settings.timeout_seconds,
        max_attempts=guardian_settings.retries + 1,
        log_path="guardian_test.log",
    )
    adapter = OpenAIChatAdapter(settings)
    print(f"\n✓ OpenAIChatAdapter initialized with {settings.base_url}")
    return adapter


@pytest.fixture
def guardian_behavior(llm_chat_adapter, guardian_settings):
    """Create GuardianBehavior instance."""
    return GuardianBehavior(chat_port=llm_chat_adapter, settings=guardian_settings)


@pytest.fixture(autouse=True)
def configure_logging():
    """Setup logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("guardian_test.log")],
    )


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end (requires real LLM)")
    config.addinivalue_line("markers", "slow: marks tests as slow (may take time with LLM)")

