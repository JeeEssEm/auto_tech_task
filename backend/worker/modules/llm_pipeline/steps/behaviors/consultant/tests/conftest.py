"""
Pytest configuration and fixtures for ConsultantBehavior E2E tests.

These tests use a real LLM adapter and mocked consultant tools
(search_gkg, get_gkg_node_detail, search_raw_sources) so test scenarios
stay deterministic while agent loop remains fully real.
"""

import asyncio
import logging

import pytest

from backend.worker.modules.llm_pipeline.providers.configs.openai_settings import OpenAIChatSettings
from backend.worker.modules.llm_pipeline.providers.openai_adapter import OpenAIChatAdapter
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.config import ConsultantSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.consultant_behavior import ConsultantBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.context import ProjectSnapshot
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.tests.mock_tools import MockConsultantTools


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def consultant_settings():
    """Load Consultant settings from environment variables."""
    try:
        settings = ConsultantSettings()
        print("\n✓ Consultant settings loaded:")
        print(f"  Provider: {settings.provider}")
        print(f"  Base URL: {settings.base_url}")
        print(f"  Model: {settings.model}")
        print(f"  Max tokens: {settings.max_tokens}")
        print(f"  Max tool calls: {settings.max_tool_calls}")
        return settings
    except Exception as e:
        pytest.skip(f"Failed to load Consultant settings: {e}")


@pytest.fixture
def llm_chat_adapter(consultant_settings):
    """Create OpenAIChatAdapter with settings from Consultant config."""
    settings = OpenAIChatSettings(
        base_url=consultant_settings.base_url,
        api_key=consultant_settings.api_key,
        temperature=consultant_settings.temperature,
        max_tokens=consultant_settings.max_tokens,
        timeout_seconds=consultant_settings.timeout_seconds,
        max_attempts=3,
        log_path="consultant_test.log",
    )
    adapter = OpenAIChatAdapter(settings)
    print(f"\n✓ OpenAIChatAdapter initialized with {settings.base_url}")
    return adapter


@pytest.fixture
def mock_consultant_tools():
    """Mocked tools backend for consultant agent loop."""
    return MockConsultantTools()


@pytest.fixture
def project_snapshot():
    """Stable project snapshot for all consultant e2e scenarios."""
    return ProjectSnapshot(
        project_name="AutoTech Task",
        project_type="TZ generation backend",
        total_gkg_nodes=143,
        unresolved_conflicts=1,
        doc_section_titles=[
            "1. Цели проекта",
            "2. Архитектура решения",
            "3. Backend API",
            "4. Хранилище данных",
            "5. Аутентификация и безопасность",
            "6. Нефункциональные требования",
        ],
        top_scopes=["База данных", "API", "Бэкенд", "Безопасность", "Интеграции"],
    )


@pytest.fixture
def consultant_behavior(llm_chat_adapter, mock_consultant_tools, consultant_settings):
    """Create ConsultantBehavior with real LLM and mocked tools."""
    return ConsultantBehavior(
        chat_port=llm_chat_adapter,
        context=mock_consultant_tools,
        settings=consultant_settings,
    )


@pytest.fixture(autouse=True)
def configure_logging():
    """Setup logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("consultant_test.log")],
    )


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end (requires real LLM)")
    config.addinivalue_line("markers", "slow: marks tests as slow (multiple tool rounds + LLM)")
