"""
Pytest configuration and fixtures for GroupingJudgeBehavior E2E tests.

These tests use:
- real LLM via OpenAI-compatible endpoint
- real embedder via FastEmbedEmbeddingPort + NodeEmbedder
- real pipeline flow StagingNode -> EmbeddedStagingNode -> GroupingJudgeBehavior
"""

import asyncio
import logging
from types import SimpleNamespace

import pytest

from backend.worker.modules.llm_pipeline.providers.configs.embedder_settings import EmbedderSettings
from backend.worker.modules.llm_pipeline.providers.configs.openai_settings import OpenAIChatSettings
from backend.worker.modules.llm_pipeline.providers.fastembed_port import FastEmbedEmbeddingPort
from backend.worker.modules.llm_pipeline.providers.openai_adapter import OpenAIChatAdapter
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.config import GroupingJudgeSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.judge import GroupingJudgeBehavior
from backend.worker.modules.llm_pipeline.steps.embedder.node_embedder import NodeEmbedder


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def grouping_judge_settings():
    """Load GroupingJudge settings from env variables."""
    try:
        settings = GroupingJudgeSettings()
        print("\n✓ GroupingJudge settings loaded:")
        print(f"  Provider: {settings.provider}")
        print(f"  Base URL: {settings.base_url}")
        print(f"  Model: {settings.model}")
        print(f"  Max tokens: {settings.max_tokens}")
        print(f"  Semantic threshold: {settings.semantic_threshold}")
        return settings
    except Exception as e:
        pytest.skip(f"Failed to load GroupingJudge settings: {e}")


@pytest.fixture
def grouping_judge_runtime_settings(grouping_judge_settings):
    """
    Runtime settings object for GroupingJudgeBehavior.

    GroupingJudgeBehavior expects `judge_model`, while config currently has `model`.
    This adapter object keeps tests non-invasive and avoids production code changes.
    """
    s = grouping_judge_settings
    return GroupingJudgeSettings(
        model=s.model,
        temperature=s.temperature,
        max_tokens=s.max_tokens,
        judge_concurrency=s.judge_concurrency,
        semantic_threshold=s.semantic_threshold,
        base_url="https://openrouter.ai/api/v1"
    )


@pytest.fixture
def llm_chat_adapter(grouping_judge_settings):
    """Create real LLM adapter for judge calls."""
    settings = OpenAIChatSettings(
        base_url=grouping_judge_settings.base_url,
        api_key=grouping_judge_settings.api_key,
        temperature=grouping_judge_settings.temperature,
        max_tokens=grouping_judge_settings.max_tokens,
        timeout_seconds=grouping_judge_settings.timeout_seconds,
        max_attempts=3,
        log_path="grouping_judge_test.log",
    )
    adapter = OpenAIChatAdapter(settings)
    print(f"\n✓ OpenAIChatAdapter initialized with {settings.base_url}")
    return adapter


@pytest.fixture
def grouping_judge_behavior(llm_chat_adapter, grouping_judge_runtime_settings):
    """Create GroupingJudgeBehavior instance."""
    return GroupingJudgeBehavior(
        chat_port=llm_chat_adapter,
        settings=grouping_judge_runtime_settings,
    )


@pytest.fixture
def node_embedder():
    """Create real embedder pipeline stage."""
    embedder_settings = EmbedderSettings()
    embed_port = FastEmbedEmbeddingPort(model_name=embedder_settings.model)
    return NodeEmbedder(embedder=embed_port, settings=embedder_settings)


@pytest.fixture(autouse=True)
def configure_logging():
    """Setup logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("grouping_judge_test.log")],
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end (requires real LLM)")
    config.addinivalue_line("markers", "slow: marks tests as slow (real embedding + LLM)")
