from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.worker.modules.llm_pipeline.orchestrator.local_contexts import (
    LocalArchitectContext,
    LocalConsultantContext,
)
from backend.worker.modules.llm_pipeline.orchestrator.local_store import LocalJSONGraphStore
from backend.worker.modules.llm_pipeline.orchestrator.nodes import OrchestratorDeps
from backend.worker.modules.llm_pipeline.providers.configs.embedder_settings import EmbedderSettings
from backend.worker.modules.llm_pipeline.providers.configs.openai_settings import OpenAIChatSettings
from backend.worker.modules.llm_pipeline.providers.fastembed_port import FastEmbedEmbeddingPort
from backend.worker.modules.llm_pipeline.providers.openai_adapter import OpenAIChatAdapter
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.architect_behavior import ArchitectBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.config import ArchitectSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.config import ConsultantSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.consultant_behavior import ConsultantBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.config import GroupingJudgeSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.judge import GroupingJudgeBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.guardian.guardian_behavior import GuardianBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.config import HarvesterSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.harvester_behavior import HarvesterBehavior
from backend.worker.modules.llm_pipeline.steps.embedder.node_embedder import NodeEmbedder
from backend.worker.modules.llm_pipeline.steps.intent_router.config import IntentRouterSettings
from backend.worker.modules.llm_pipeline.steps.intent_router.intent_router import IntentRouter


@dataclass
class LocalOrchestratorRuntime:
    deps: OrchestratorDeps
    store: LocalJSONGraphStore



def _build_adapter(
    base_url: str,
    api_key: str | None,
    temperature: float,
    max_tokens: int,
    timeout_seconds: float,
    log_path: str,
) -> OpenAIChatAdapter:
    return OpenAIChatAdapter(
        OpenAIChatSettings(
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            max_attempts=3,
            log_path=log_path,
        )
    )


async def create_local_runtime(state_path: str | Path) -> LocalOrchestratorRuntime:
    store = LocalJSONGraphStore(state_path=Path(state_path))
    await store.load()

    intent_settings = IntentRouterSettings()
    consultant_settings = ConsultantSettings()
    architect_settings = ArchitectSettings()
    harvester_settings = HarvesterSettings()
    grouping_settings = GroupingJudgeSettings()

    intent_adapter = _build_adapter(
        intent_settings.base_url,
        intent_settings.api_key,
        intent_settings.temperature,
        intent_settings.max_tokens,
        intent_settings.timeout_seconds,
        "orchestrator_router.log",
    )
    consultant_adapter = _build_adapter(
        consultant_settings.base_url,
        consultant_settings.api_key,
        consultant_settings.temperature,
        consultant_settings.max_tokens,
        consultant_settings.timeout_seconds,
        "orchestrator_consultant.log",
    )
    architect_adapter = _build_adapter(
        architect_settings.base_url,
        architect_settings.api_key,
        architect_settings.temperature,
        architect_settings.max_tokens,
        architect_settings.timeout_seconds,
        "orchestrator_architect.log",
    )
    harvester_adapter = _build_adapter(
        harvester_settings.base_url,
        harvester_settings.api_key,
        0.1,
        harvester_settings.max_tokens,
        harvester_settings.timeout_seconds,
        "orchestrator_harvester.log",
    )
    grouping_adapter = _build_adapter(
        grouping_settings.base_url,
        grouping_settings.api_key,
        grouping_settings.temperature,
        grouping_settings.max_tokens,
        grouping_settings.timeout_seconds,
        "orchestrator_grouping.log",
    )

    embedder_settings = EmbedderSettings()
    embedder_port = FastEmbedEmbeddingPort(embedder_settings.model)

    consultant_context = LocalConsultantContext(store)
    architect_context = LocalArchitectContext(store)

    async def _get_project_snapshot(project_id: int):
        return await store.get_project_snapshot(project_id)

    async def _get_affected_sections(project_id: int, gkg_nodes):
        return await store.get_affected_sections(project_id, gkg_nodes)

    async def _persist_gkg(project_id: int, gkg_nodes, pending_conflicts):
        await store.persist_gkg(project_id, gkg_nodes, pending_conflicts)

    async def _load_existing(project_id: int, pairs: set[tuple[str, str]]):
        return await store.get_existing_embedded_nodes(project_id, pairs)

    async def _gkg_snapshot(project_id: int):
        return await store.get_gkg_snapshot_text(project_id)

    async def _doc_snapshot(project_id: int):
        return await store.get_doc_snapshot_text(project_id)

    async def _pending(project_id: int):
        return await store.get_pending_action_questions(project_id)

    async def _capture_raw_source(project_id: int, source_id: str, source_name: str, text: str):
        await store.capture_raw_source(project_id, source_id, source_name, text)

    async def _save_doc_updates(project_id: int, updates):
        await store.apply_document_updates(project_id, updates)

    async def _build_document_snapshot(project_id: int, block_id: str, trigger_reason: str):
        return await store.build_document_snapshot(project_id, block_id, trigger_reason)

    async def _resolve_pending_action(project_id: int, action_id: str, resolution: str):
        return await store.resolve_pending_action(project_id, action_id, resolution)

    async def _mark_block_manual(project_id: int, block_id: str, content_md: str):
        await store.mark_block_manual(project_id, block_id, content_md)

    deps = OrchestratorDeps(
        intent_router=IntentRouter(intent_adapter, intent_settings),
        guardian=GuardianBehavior(intent_adapter, intent_settings),
        harvester=HarvesterBehavior(harvester_adapter, harvester_settings),
        consultant=ConsultantBehavior(consultant_adapter, consultant_context, consultant_settings),
        grouping_judge=GroupingJudgeBehavior(grouping_adapter, grouping_settings),
        architect=ArchitectBehavior(architect_adapter, architect_context, architect_settings),
        embedder=NodeEmbedder(embedder_port, embedder_settings),
        get_project_snapshot=_get_project_snapshot,
        get_affected_sections=_get_affected_sections,
        persist_gkg=_persist_gkg,
        load_existing_gkg_nodes=_load_existing,
        get_gkg_snapshot=_gkg_snapshot,
        get_doc_snapshot=_doc_snapshot,
        get_pending_actions=_pending,
        consultant_context=consultant_context,
        architect_context=architect_context,
        capture_raw_source=_capture_raw_source,
        save_document_updates=_save_doc_updates,
        build_document_snapshot=_build_document_snapshot,
        resolve_pending_action=_resolve_pending_action,
        mark_block_manual=_mark_block_manual,
    )

    return LocalOrchestratorRuntime(deps=deps, store=store)


async def create_local_deps(state_path: str | Path) -> OrchestratorDeps:
    runtime = await create_local_runtime(state_path)
    return runtime.deps
