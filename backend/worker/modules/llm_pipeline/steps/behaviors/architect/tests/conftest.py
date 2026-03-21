"""
Pytest fixtures for ArchitectBehavior E2E tests.

These tests use a real LLM adapter and mocked architect tools
(get_context_details, search_raw_sources, ask_user, validate_consistency).
"""

import asyncio
import logging

import pytest

from backend.worker.modules.llm_pipeline.providers.configs.openai_settings import OpenAIChatSettings
from backend.worker.modules.llm_pipeline.providers.openai_adapter import OpenAIChatAdapter
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.architect_behavior import ArchitectBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.config import ArchitectSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.tests.mock_tools import MockArchitectTools


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
    """Create OpenAIChatAdapter with settings from Architect config."""
    settings = OpenAIChatSettings(
        base_url=architect_settings.base_url,
        api_key=architect_settings.api_key,
        temperature=architect_settings.temperature,
        max_tokens=architect_settings.max_tokens,
        timeout_seconds=architect_settings.timeout_seconds,
        max_attempts=3,
        log_path="architect_test.log",
    )
    adapter = OpenAIChatAdapter(settings)
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
