import asyncio

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end (requires real LLM)")
    config.addinivalue_line("markers", "slow: marks tests as slow")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
