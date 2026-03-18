"""
Pytest configuration and fixtures for IntentRouter E2E tests.
"""

import asyncio
import logging
from typing import AsyncGenerator

import pytest

from backend.worker.modules.llm_pipeline.providers.openai_adapter import OpenAIChatAdapter
from backend.worker.modules.llm_pipeline.providers.configs.openai_settings import OpenAIChatSettings
from backend.worker.modules.llm_pipeline.steps.intent_router.intent_router import IntentRouter
from backend.worker.modules.llm_pipeline.steps.intent_router.config import IntentRouterSettings
from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import (
    IntentRouterRequest,
    IntentRouterResponse,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def intent_router_settings():
    """Load IntentRouter settings from environment variables."""
    try:
        settings = IntentRouterSettings()
        print(f"\n✓ IntentRouter settings loaded:")
        print(f"  Provider: {settings.provider}")
        print(f"  Base URL: {settings.base_url}")
        print(f"  Model: {settings.model}")
        print(f"  Temperature: {settings.temperature}")
        print(f"  Max tokens: {settings.max_tokens}")
        return settings
    except Exception as e:
        pytest.skip(f"Failed to load IntentRouter settings: {e}")


@pytest.fixture
def llm_chat_adapter(intent_router_settings):
    """Create OpenAIChatAdapter with settings from IntentRouter config."""
    settings = OpenAIChatSettings(
        base_url=intent_router_settings.base_url,
        api_key=intent_router_settings.api_key,
        temperature=intent_router_settings.temperature,
        max_tokens=intent_router_settings.max_tokens,
        timeout_seconds=intent_router_settings.timeout_seconds,
        max_attempts=intent_router_settings.retries + 1,
        log_path="intent_router_test.log",
    )
    adapter = OpenAIChatAdapter(settings)
    print(f"\n✓ OpenAIChatAdapter initialized with {settings.base_url}")
    return adapter


@pytest.fixture
def intent_router(llm_chat_adapter, intent_router_settings):
    """Create IntentRouter instance."""
    router = IntentRouter(llm_chat_adapter, intent_router_settings)
    print(f"\n✓ IntentRouter instance created")
    return router


# Configure logging
@pytest.fixture(autouse=True)
def configure_logging():
    """Setup logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("intent_router_test.log"),
        ],
    )


# Test markers
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end (requires real LLM)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (may take time with LLM)"
    )


# Helper functions for test data
class TestDataProvider:
    """Provides test data for various scenarios."""

    @staticmethod
    def architect_scenarios():
        """Scenarios that should activate Architect behavior."""
        return [
            IntentRouterRequest(
                user_prompt="перегенируй блок ТЗ с требованием к СУБД, поставь MySQL",
                attachments=[],
            ),
            IntentRouterRequest(
                user_prompt="Обновить раздел про безопасность - нужна OAuth2",
                attachments=[],
            ),
            IntentRouterRequest(
                user_prompt="Добавь требование к кэшированию Redis",
                attachments=[],
            ),
        ]

    @staticmethod
    def consultant_scenarios():
        """Scenarios that should activate Consultant behavior."""
        return [
            IntentRouterRequest(
                user_prompt="Какие у нас требования к API?",
                attachments=[],
            ),
            IntentRouterRequest(
                user_prompt="Расскажи про обработку ошибок",
                attachments=[],
            ),
            IntentRouterRequest(
                user_prompt="Как выглядит архитектура системы?",
                attachments=[],
            ),
        ]

    @staticmethod
    def harvester_scenarios():
        """Scenarios that should activate Harvester behavior."""
        return [
            IntentRouterRequest(
                user_prompt="Пользователь может быть админом или обычным юзером",
                attachments=[],
            ),
            IntentRouterRequest(
                user_prompt="Система должна поддерживать экспорт в PDF, CSV, XLSX",
                attachments=[],
            ),
            IntentRouterRequest(
                user_prompt="Максимальный размер экспорта - 100K записей",
                attachments=[],
            ),
        ]

    @staticmethod
    def guardian_scenarios():
        """Scenarios that should activate Guardian behavior (off-topic)."""
        return [
            IntentRouterRequest(
                user_prompt="Напиши мне код быстрой сортировки на Python",
                attachments=[],
            ),
            IntentRouterRequest(
                user_prompt="Как приготовить пасту?",
                attachments=[],
            ),
            IntentRouterRequest(
                user_prompt="Порекомендуй хороший ресторан",
                attachments=[],
            ),
        ]

    @staticmethod
    def mixed_scenarios():
        """Scenarios with multiple behaviors."""
        return [
            IntentRouterRequest(
                user_prompt=(
                    "перегенируй блок ТЗ с требованием к СУБД, поставь mysql, "
                    "и еще напиши код быстрой сортировки"
                ),
                attachments=[],
            ),
            IntentRouterRequest(
                user_prompt=(
                    "У каждого пользователя есть личный кабинет. "
                    "Какие требования это добавляет?"
                ),
                attachments=[],
            ),
        ]


@pytest.fixture
def test_data():
    """Provide test data."""
    return TestDataProvider()
