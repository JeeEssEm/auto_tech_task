import asyncio
from pathlib import Path

import pytest

from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.staging import StagingNode


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[8]


def _load_real_source_text() -> str:
    repo_root = _repo_root()
    primary = repo_root / "docs" / "ml_pipeline" / "02_step1_extraction.md"
    fallback = repo_root / "Большое ТЗ.md"

    for candidate in (primary, fallback):
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text

    raise AssertionError(
        "No real source file found for Harvester e2e tests. "
        "Expected docs/ml_pipeline/02_step1_extraction.md or Большое ТЗ.md"
    )


def _assert_staging_nodes(nodes: list[StagingNode]) -> None:
    assert isinstance(nodes, list)
    assert nodes, "Harvester produced no staging nodes"
    for node in nodes:
        assert isinstance(node, StagingNode)
        assert node.source_id.strip(), "source_id must be non-empty"
        assert node.scope.strip(), "scope must be non-empty"
        assert node.property.strip(), "property must be non-empty"
        assert node.value.strip(), "value must be non-empty"
        assert node.content_raw.strip(), "content_raw must be non-empty"
        assert isinstance(node.chunk_index, int)
        assert node.chunk_index >= 0


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_harvester_process_real_document(harvester_behavior):
    text = _load_real_source_text()
    response = await harvester_behavior.process_source(
        source_id="harvester-e2e-real-doc",
        text=text,
        source_meta="Реальный документ ml_pipeline для extraction step",
    )
    print(f"\n[harvester/real-doc] staging nodes: {len(response)}")
    _assert_staging_nodes(response)


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_harvester_process_real_document_long_input(harvester_behavior):
    # Repeat real source to force multi-chunk processing and AWM continuity checks.
    text = "\n\n".join([_load_real_source_text()] * 3)
    response = await harvester_behavior.process_source(
        source_id="harvester-e2e-long-real-doc",
        text=text,
        source_meta="Реальный документ x3 для стресс-проверки чанков",
    )
    print(f"\n[harvester/real-doc/long] staging nodes: {len(response)}")
    _assert_staging_nodes(response)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_harvester_concurrent_real_sources(harvester_behavior):
    text = _load_real_source_text()
    half = max(1, len(text) // 2)

    coroutines = [
        harvester_behavior.process_source(
            source_id="harvester-e2e-concurrent-a",
            text=text[:half],
            source_meta="Часть A реального документа",
        ),
        harvester_behavior.process_source(
            source_id="harvester-e2e-concurrent-b",
            text=text[half:],
            source_meta="Часть B реального документа",
        ),
    ]

    results = await asyncio.gather(*coroutines)
    assert len(results) == 2

    for idx, nodes in enumerate(results, start=1):
        print(f"\n[harvester/concurrent/{idx}] staging nodes: {len(nodes)}")
        _assert_staging_nodes(nodes)


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_harvester_process_dialog(harvester_behavior):
    text = Path(r"C:\Users\JeeEssEm\Desktop\ChatExport_2026-03-07\chat_dataset_small.txt").read_text(encoding="utf-8")
    response = await harvester_behavior.process_source(
        source_id="dialog-pogromisty",
        text=text,
        source_meta="Диалог авто тз",
    )
    print(f"\n[harvester/real-doc/long] staging nodes: {len(response)}")
    _assert_staging_nodes(response) # 1 hour


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_harvester_process_dialog_mini(harvester_behavior):
    text = Path(r"C:\Users\JeeEssEm\Desktop\ChatExport_2026-03-07\mini_dialog.txt").read_text(encoding="utf-8")
    response = await harvester_behavior.process_source(
        source_id="dialog-pogromisty",
        text=text,
        source_meta="Диалог авто тз",
    )
    print(f"\n[harvester/real-doc/long] staging nodes: {len(response)}") # 23 min
    _assert_staging_nodes(response)
