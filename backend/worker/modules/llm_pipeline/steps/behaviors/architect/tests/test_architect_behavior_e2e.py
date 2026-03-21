import asyncio
import json
import os
from pathlib import Path

import pytest

from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.schemas import (
    DocumentSnapshot,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import (
    ArchitectResponse,
    GKGFact,
    WrittenSection,
)


def _assert_architect_response(response: ArchitectResponse) -> None:
    assert isinstance(response, ArchitectResponse)
    assert isinstance(response.section_id, str)
    assert response.section_id.strip(), "section_id must be non-empty"
    assert response.status in {"generated", "partial", "missing"}
    assert isinstance(response.pending_actions, list)
    assert isinstance(response.used_tool_calls, int)
    assert response.used_tool_calls >= 0


def _base_written_sections() -> list[WrittenSection]:
    return [
        WrittenSection(
            section_id="sec_intro",
            title="Общее описание",
            content_md=(
                "Проект использует Python/FastAPI backend и ориентирован на аналитические сценарии."
            ),
        )
    ]


def _tech_stack_snapshot() -> DocumentSnapshot:
    return DocumentSnapshot(
        section_id="sec_tech_stack",
        section_title="Стек технологий",
        section_level=2,
        section_required=True,
        context_hint="Языки, фреймворки, СУБД, брокеры сообщений",
        trigger_reason="initial_generation",
        section_facts=[
            GKGFact(
                topic_id="backend_framework",
                scope="Бэкенд",
                property="Фреймворк",
                value="FastAPI",
                status="RESOLVED",
                source_ids=["chat-11"],
            ),
            GKGFact(
                topic_id="db_engine_main",
                scope="База данных",
                property="Движок",
                value="ClickHouse",
                status="RESOLVED",
                source_ids=["chat-102", "decision-log-7"],
            ),
            GKGFact(
                topic_id="auth_method",
                scope="API",
                property="Аутентификация",
                value="JWT access + refresh",
                status="NO_CONFLICT",
                source_ids=["chat-33"],
            ),
        ],
        written_sections=_base_written_sections(),
    )


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_architect_generates_section_from_facts(
    architect_behavior,
    mock_architect_tools,
):
    snapshot = _tech_stack_snapshot()
    response = await architect_behavior.run(snapshot=snapshot)

    print("\n[architect/tech-stack]", response.content_md)
    _assert_architect_response(response)

    assert response.section_id == snapshot.section_id
    assert response.status in {"generated", "partial"}
    assert response.content_md.strip(), "Expected generated markdown content"

    content_lc = response.content_md.lower()
    assert "fastapi" in content_lc or "clickhouse" in content_lc
    assert response.used_tool_calls <= architect_behavior._settings.max_tool_calls

    called_tools = {c.tool_name for c in mock_architect_tools.calls}
    assert len(called_tools) > 0, "Expected architect to use at least one tool"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_architect_required_missing_data_creates_pending_or_missing_marker(
    architect_behavior,
):
    snapshot = DocumentSnapshot(
        section_id="sec_queue",
        section_title="Брокер сообщений",
        section_level=2,
        section_required=True,
        context_hint="Тип брокера, гарантии доставки, ретраи, DLQ",
        trigger_reason="initial_generation",
        section_facts=[],
        written_sections=_base_written_sections(),
    )

    response = await architect_behavior.run(snapshot=snapshot)

    print("\n[architect/missing-required]", response.content_md)
    _assert_architect_response(response)

    assert response.section_id == snapshot.section_id
    assert response.used_tool_calls <= architect_behavior._settings.max_tool_calls

    has_pending = len(response.pending_actions) > 0
    has_missing_marker = "[ДАННЫЕ ОТСУТСТВУЮТ" in response.content_md
    assert has_pending or has_missing_marker or response.status == "missing"


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_architect_concurrent_sections(
    architect_behavior,
):
    snapshots = [
        _tech_stack_snapshot(),
        DocumentSnapshot(
            section_id="sec_auth",
            section_title="Аутентификация",
            section_level=2,
            section_required=True,
            context_hint="Методы auth, access/refresh токены, ttl",
            trigger_reason="spec_block_affected",
            section_facts=[
                GKGFact(
                    topic_id="auth_method",
                    scope="API",
                    property="Аутентификация",
                    value="JWT access + refresh",
                    status="NO_CONFLICT",
                    source_ids=["chat-33"],
                ),
            ],
            written_sections=_base_written_sections(),
        ),
        DocumentSnapshot(
            section_id="sec_backend",
            section_title="Backend",
            section_level=2,
            section_required=True,
            context_hint="Язык, фреймворк, API стиль",
            trigger_reason="explicit_regen_request",
            section_facts=[
                GKGFact(
                    topic_id="backend_framework",
                    scope="Бэкенд",
                    property="Фреймворк",
                    value="FastAPI",
                    status="RESOLVED",
                    source_ids=["chat-11"],
                ),
            ],
            written_sections=_base_written_sections(),
        ),
    ]

    responses = await asyncio.gather(*[architect_behavior.run(snapshot=s) for s in snapshots])

    assert len(responses) == len(snapshots)
    for response, snapshot in zip(responses, snapshots):
        _assert_architect_response(response)
        assert response.section_id == snapshot.section_id
        assert response.used_tool_calls <= architect_behavior._settings.max_tool_calls


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_architect_manual_snapshot_from_env(
    architect_behavior,
):
    """
    Manual poke mode for local checks.

    If ARCHITECT_E2E_SNAPSHOT_JSON points to a JSON file,
    this test will run with that custom DocumentSnapshot payload.
    Otherwise it uses default tech stack snapshot.
    """
    json_path = os.getenv("ARCHITECT_E2E_SNAPSHOT_JSON", "").strip()

    if json_path:
        payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
        snapshot = DocumentSnapshot(**payload)
    else:
        snapshot = _tech_stack_snapshot()

    response = await architect_behavior.run(snapshot=snapshot)

    print("\n[architect/manual] section_id=", snapshot.section_id)
    print("[architect/manual] status=", response.status)
    print("[architect/manual] pending_actions=", [a.model_dump() for a in response.pending_actions])
    print("[architect/manual] content_md=", response.content_md)

    _assert_architect_response(response)
