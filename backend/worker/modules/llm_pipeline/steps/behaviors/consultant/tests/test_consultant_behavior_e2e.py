import asyncio
import os

import pytest

from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.schemas import ConsultantResponse


def _assert_consultant_response(response: ConsultantResponse) -> None:
    assert isinstance(response, ConsultantResponse)
    assert isinstance(response.answer, str)
    assert response.answer.strip(), "Consultant answer must be non-empty"
    assert isinstance(response.used_tool_calls, int)
    assert response.used_tool_calls >= 0
    assert isinstance(response.source_refs, list)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_consultant_answers_db_choice_with_mocked_tools(
    consultant_behavior,
    project_snapshot,
    mock_consultant_tools,
):
    question = "Почему в проекте выбрали ClickHouse, а не Postgres?"
    response = await consultant_behavior.run(question=question, snapshot=project_snapshot)

    print("\n[consultant/db-choice]", response.answer)
    _assert_consultant_response(response)

    answer_lc = response.answer.lower()
    assert "clickhouse" in answer_lc
    assert "postgres" in answer_lc or "postgresql" in answer_lc

    called_tools = [c.tool_name for c in mock_consultant_tools.calls]
    assert "search_gkg" in called_tools, "Consultant should start from search_gkg"
    assert response.used_tool_calls <= consultant_behavior._settings.max_tool_calls


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_consultant_answers_auth_question(
    consultant_behavior,
    project_snapshot,
    mock_consultant_tools,
):
    question = "Какая у нас схема аутентификации и зачем refresh token?"
    response = await consultant_behavior.run(question=question, snapshot=project_snapshot)

    print("\n[consultant/auth]", response.answer)
    _assert_consultant_response(response)

    answer_lc = response.answer.lower()
    assert "jwt" in answer_lc
    assert "refresh" in answer_lc
    assert any(c.tool_name == "search_gkg" for c in mock_consultant_tools.calls)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_consultant_handles_unknown_question_without_hallucinations(
    consultant_behavior,
    project_snapshot,
):
    question = "Сколько у нас дата-центров в Южной Америке и где стоит edge-кластер?"
    response = await consultant_behavior.run(question=question, snapshot=project_snapshot)

    print("\n[consultant/unknown]", response.answer)
    _assert_consultant_response(response)

    answer_lc = response.answer.lower()
    soft_indicators = ["нет", "не найден", "недостаточно", "не указано", "не хватает"]
    assert any(marker in answer_lc for marker in soft_indicators)


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_consultant_concurrent_questions(
    consultant_behavior,
    project_snapshot,
):
    questions = [
        "Почему выбрали ClickHouse?",
        "Какой backend framework принят?",
        "Какая схема auth используется в API?",
    ]

    coros = [consultant_behavior.run(question=q, snapshot=project_snapshot) for q in questions]
    responses = await asyncio.gather(*coros)

    assert len(responses) == len(questions)
    for response in responses:
        _assert_consultant_response(response)
        assert response.used_tool_calls <= consultant_behavior._settings.max_tool_calls


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_consultant_manual_question_from_env(
    consultant_behavior,
    project_snapshot,
):
    """
    Manual poke mode for quick local checks.

    Use env var CONSULTANT_E2E_QUESTION to override the question,
    otherwise test uses a safe default business question.
    """
    question = os.getenv(
        "CONSULTANT_E2E_QUESTION",
        "Сформулируй кратко, какие архитектурные решения уже зафиксированы по БД и API.",
    ).strip()

    response = await consultant_behavior.run(question=question, snapshot=project_snapshot)

    print(f"\n[consultant/manual] question={question}")
    print("[consultant/manual] answer=", response.answer)
    print("[consultant/manual] refs=", response.source_refs)

    _assert_consultant_response(response)
