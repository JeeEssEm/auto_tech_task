import datetime
import json
import os
import time
from pathlib import Path

import pytest

from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.staging import StagingNode


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[8]


def _default_staging_nodes() -> list[StagingNode]:
    """
    Default real-like nodes for e2e tests.

    The set intentionally contains:
    - potential duplicates
    - potential conflict in one property
    - one independent fact
    """
    return [
        StagingNode(
            source_id="src-chat-1",
            scope="База данных",
            property="Движок",
            value="PostgreSQL",
            content_raw="Предлагаю использовать PostgreSQL как основную СУБД.",
            author="Алексей",
            timestamp="2026-03-19T10:00:00Z",
            chunk_index=0,
        ),
        StagingNode(
            source_id="src-chat-2",
            scope="База данных",
            property="Движок",
            value="Postgres",
            content_raw="Сходимся на Postgres, это наш основной вариант.",
            author="Мария",
            timestamp="2026-03-19T10:01:00Z",
            chunk_index=0,
        ),
        StagingNode(
            source_id="src-chat-3",
            scope="База данных",
            property="Движок",
            value="ClickHouse",
            content_raw="Для аналитики лучше ClickHouse, а не Postgres.",
            author="Иван",
            timestamp="2026-03-19T10:02:00Z",
            chunk_index=0,
        ),
        StagingNode(
            source_id="src-chat-4",
            scope="Бэкенд",
            property="Язык",
            value="Python",
            content_raw="Бэкенд пишем на Python/FastAPI.",
            author="Ольга",
            timestamp="2026-03-19T10:05:00Z",
            chunk_index=1,
        ),
    ]


def _load_staging_nodes_from_json_file(file_path: str) -> list[StagingNode]:
    """
    Extension point: load list[StagingNode] from arbitrary JSON file on disk.

    Supported JSON shapes:
    - [ {StagingNode...}, ... ]
    - { "nodes": [ {StagingNode...}, ... ] }
    """
    payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        raw_nodes = payload
    elif isinstance(payload, dict) and isinstance(payload.get("nodes"), list):
        raw_nodes = payload["nodes"]
    else:
        raise AssertionError("Unsupported JSON shape for staging nodes")

    return [StagingNode.model_validate(item) for item in raw_nodes]


def _build_input_nodes() -> list[StagingNode]:
    # Keep room for external dataset injection from disk.
    # Example:
    #   set GROUPING_JUDGE_E2E_STAGING_JSON=E:/datasets/my_nodes.json
    # json_path = os.getenv("GROUPING_JUDGE_E2E_STAGING_JSON", "").strip()
    json_path = r"C:\Users\JeeEssEm\Desktop\ChatExport_2026-03-07\nodes_old_small_chat.json"
    if json_path:
        candidate = Path(json_path)
        if not candidate.exists():
            raise AssertionError(f"JSON file not found: {candidate}")
        return _load_staging_nodes_from_json_file(str(candidate))

    return _default_staging_nodes()


def _assert_grouping_judge_result(result) -> None:
    assert hasattr(result, "gkg_nodes")
    assert hasattr(result, "pending_conflicts")

    assert isinstance(result.gkg_nodes, list)
    assert isinstance(result.pending_conflicts, list)

    total_items = len(result.gkg_nodes) + len(result.pending_conflicts)
    assert total_items > 0, "GroupingJudge produced no output"

    for node in result.gkg_nodes:
        assert node.scope.strip()
        assert node.property.strip()
        assert node.value.strip()
        assert node.content_raw.strip()
        assert isinstance(node.source_ids, list)
        assert node.source_ids
        assert isinstance(node.embedding, list)
        assert node.embedding

    for conflict in result.pending_conflicts:
        assert conflict.scope.strip()
        assert conflict.property.strip()
        assert isinstance(conflict.options, list)
        assert conflict.options


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_grouping_judge_e2e_with_real_embedder_and_llm(grouping_judge_behavior, node_embedder):
    staging_nodes = _build_input_nodes()

    # Mandatory preprocessing stage for this e2e: StagingNode -> EmbeddedStagingNode.
    print(f"started embedding: {time.perf_counter()}")
    embedded_nodes = await node_embedder.execute(staging_nodes)
    print(f"ended embedding: {time.perf_counter()}")
    result = await grouping_judge_behavior.run(embedded_nodes)

    path = Path(fr"C:\Users\JeeEssEm\Desktop\ChatExport_2026-03-07\dump_embedded_nodes_{datetime.datetime.now().strftime('%Y-%m-%d %H-%M')}.json")
    for row in result.gkg_nodes:
        row.embedding = []
    path.write_text(json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf8")

    print(f"ended grouping: {time.perf_counter()}")
    print(
        "\n[grouping_judge/e2e] "
        f"embedded={len(embedded_nodes)} "
        f"gkg_nodes={len(result.gkg_nodes)} "
        f"pending_conflicts={len(result.pending_conflicts)}"
    )
    _assert_grouping_judge_result(result)


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_grouping_judge_e2e_external_json_is_supported(grouping_judge_behavior, node_embedder):
    """
    If GROUPING_JUDGE_E2E_STAGING_JSON is set, test runs strictly on that file.
    Otherwise it falls back to default fixture data.
    """
    staging_nodes = _build_input_nodes()
    embedded_nodes = await node_embedder.execute(staging_nodes)

    result = await grouping_judge_behavior.run(embedded_nodes)
    print(
        "\n[grouping_judge/e2e/external-json] "
        f"embedded={len(embedded_nodes)} "
        f"gkg_nodes={len(result.gkg_nodes)} "
        f"pending_conflicts={len(result.pending_conflicts)}"
    )
    _assert_grouping_judge_result(result)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_grouping_judge_conflict_path_produces_resolution_or_pending(grouping_judge_behavior, node_embedder):
    conflict_nodes = [
        StagingNode(
            source_id="src-a",
            scope="API",
            property="Аутентификация",
            value="JWT",
            content_raw="Используем JWT токены для auth.",
            author="A",
            timestamp="2026-03-19T10:00:00Z",
            chunk_index=0,
        ),
        StagingNode(
            source_id="src-b",
            scope="API",
            property="Аутентификация",
            value="OAuth2",
            content_raw="Нужен OAuth2 с refresh token.",
            author="B",
            timestamp="2026-03-19T10:01:00Z",
            chunk_index=0,
        ),
    ]

    embedded_nodes = await node_embedder.execute(conflict_nodes)
    result = await grouping_judge_behavior.run(embedded_nodes)

    # Either judge resolves the conflict into gkg_nodes or leaves pending conflict.
    resolved = any(
        n.scope == "API" and n.property == "Аутентификация"
        for n in result.gkg_nodes
    )
    pending = any(
        c.scope == "API" and c.property == "Аутентификация"
        for c in result.pending_conflicts
    )

    assert resolved or pending, "Expected conflict to be resolved or surfaced as pending"
