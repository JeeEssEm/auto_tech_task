"""
Pytest configuration and fixtures for HarvesterBehavior E2E tests.

These tests call a real LLM via `OpenAIChatAdapter` using Harvester settings
from environment variables (`LLM_PIPELINE_V3_HARVESTER_*`).
"""

import asyncio
import logging

import pytest

from backend.worker.modules.llm_pipeline.providers.configs.openai_settings import OpenAIChatSettings
from backend.worker.modules.llm_pipeline.providers.openai_adapter import OpenAIChatAdapter
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.config import HarvesterSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.harvester_behavior import HarvesterBehavior


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def harvester_settings():
    """Load Harvester settings from environment variables."""
    try:
        settings = HarvesterSettings()
        print("\n✓ Harvester settings loaded:")
        print(f"  Provider: {settings.provider}")
        print(f"  Base URL: {settings.base_url}")
        print(f"  Model: {settings.model}")
        print(f"  Max tokens: {settings.max_tokens}")
        print(f"  Timeout seconds: {settings.timeout_seconds}")
        print(f"  Max self-correction retries: {settings.max_self_correction_retries}")
        print(f"  Eviction max open topics: {settings.eviction_max_open_topics}")
        return settings
    except Exception as e:
        pytest.skip(f"Failed to load Harvester settings: {e}")


@pytest.fixture
def llm_chat_adapter(harvester_settings):
    """Create OpenAIChatAdapter with settings from Harvester config."""
    settings = OpenAIChatSettings(
        base_url=harvester_settings.base_url,
        api_key=harvester_settings.api_key,
        temperature=0.1,
        max_tokens=harvester_settings.max_tokens,
        timeout_seconds=harvester_settings.timeout_seconds,
        max_attempts=3,
        log_path="harvester_test.log",
    )
    adapter = OpenAIChatAdapter(settings)
    print(f"\n✓ OpenAIChatAdapter initialized with {settings.base_url}")
    return adapter


@pytest.fixture
def harvester_behavior(llm_chat_adapter, harvester_settings):
    """Create HarvesterBehavior instance."""
    return HarvesterBehavior(chat_port=llm_chat_adapter, settings=harvester_settings)


@pytest.fixture(autouse=True)
def configure_logging():
    """Setup logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("harvester_test.log")],
    )


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end (requires real LLM)")
    config.addinivalue_line("markers", "slow: marks tests as slow (may take time with LLM)")
