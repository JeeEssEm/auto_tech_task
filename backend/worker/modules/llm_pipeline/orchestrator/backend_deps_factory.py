from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from prisma import Prisma

from backend.app.infrastructure.persistent.llm_pipeline import GKGRepository, PendingActionsRepository
from backend.worker.modules.llm_pipeline.orchestrator.nodes import OrchestratorDeps
from backend.worker.modules.llm_pipeline.orchestrator.pg_contexts import PgArchitectContext, PgConsultantContext
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


LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class BackendOrchestratorRuntime:
    deps: OrchestratorDeps
    db: Prisma
    owns_db: bool = False

    async def shutdown(self) -> None:
        if self.owns_db:
            await self.db.disconnect()


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


async def create_backend_runtime(db: Prisma | None = None) -> BackendOrchestratorRuntime:
    owns_db = db is None
    prisma = db or Prisma()
    if owns_db:
        await prisma.connect()

    execute_raw = getattr(prisma, "execute_raw", None)
    if callable(execute_raw):
        await execute_raw("CREATE EXTENSION IF NOT EXISTS vector;")

    gkg_repo = GKGRepository(prisma)
    pending_repo = PendingActionsRepository(prisma)

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
        str(LOG_DIR / "orchestrator_router.log"),
    )
    consultant_adapter = _build_adapter(
        consultant_settings.base_url,
        consultant_settings.api_key,
        consultant_settings.temperature,
        consultant_settings.max_tokens,
        consultant_settings.timeout_seconds,
        str(LOG_DIR / "orchestrator_consultant.log"),
    )
    architect_adapter = _build_adapter(
        architect_settings.base_url,
        architect_settings.api_key,
        architect_settings.temperature,
        architect_settings.max_tokens,
        architect_settings.timeout_seconds,
        str(LOG_DIR / "orchestrator_architect.log"),
    )
    harvester_adapter = _build_adapter(
        harvester_settings.base_url,
        harvester_settings.api_key,
        0.1,
        harvester_settings.max_tokens,
        harvester_settings.timeout_seconds,
        str(LOG_DIR / "orchestrator_harvester.log"),
    )
    grouping_adapter = _build_adapter(
        grouping_settings.base_url,
        grouping_settings.api_key,
        grouping_settings.temperature,
        grouping_settings.max_tokens,
        grouping_settings.timeout_seconds,
        str(LOG_DIR / "orchestrator_grouping.log"),
    )

    embedder_settings = EmbedderSettings()
    embedder_port = FastEmbedEmbeddingPort(embedder_settings.model)

    consultant_context = PgConsultantContext(gkg_repo)
    architect_context = PgArchitectContext(gkg_repo, pending_repo)

    async def _get_project_snapshot(project_id: int):
        return await gkg_repo.get_project_snapshot(project_id)

    async def _persist_gkg(project_id: int, gkg_nodes, pending_conflicts):
        await gkg_repo.persist_gkg(project_id, gkg_nodes, pending_conflicts)

    async def _load_existing(project_id: int, pairs: set[tuple[str, str]]):
        return await gkg_repo.get_existing_embedded_nodes(project_id, pairs)

    async def _gkg_snapshot(project_id: int):
        return await gkg_repo.get_gkg_snapshot_text(project_id)

    async def _doc_snapshot(project_id: int):
        return await gkg_repo.get_doc_snapshot_text(project_id)

    async def _pending(project_id: int):
        return await pending_repo.get_waiting_questions(project_id)

    async def _capture_raw_source(project_id: int, source_id: str, source_name: str, text: str):
        await gkg_repo.capture_raw_source(project_id, source_id, source_name, text)

    async def _save_doc_updates(project_id: int, updates):
        await gkg_repo.apply_document_updates(project_id, updates)

    async def _build_document_snapshot(project_id: int, block_id: str, trigger_reason: str):
        return await gkg_repo.build_document_snapshot(project_id, block_id, trigger_reason)

    async def _resolve_pending_action(project_id: int, action_id: str, resolution: str):
        resolved = await pending_repo.resolve_pending_action(project_id, action_id, resolution)
        if resolved is None:
            return []
        return await gkg_repo.create_resolved_node_from_pending_action(
            project_id=project_id,
            action_id=resolved["id"],
            question=resolved["question"],
            resolution=resolved["resolution"],
        )

    async def _mark_block_manual(project_id: int, block_id: str, content_md: str):
        await gkg_repo.mark_block_manual(project_id, block_id, content_md)

    async def _apply_template_structure(project_id: int, template_type: str):
        await gkg_repo.apply_template_sections(project_id, template_type)

    async def _list_sections(project_id: int) -> list[tuple[str, str, int, bool, str, str, bool]]:
        return await gkg_repo.list_sections(project_id)

    deps = OrchestratorDeps(
        intent_router=IntentRouter(intent_adapter, intent_settings),
        guardian=GuardianBehavior(intent_adapter, intent_settings),
        harvester=HarvesterBehavior(harvester_adapter, harvester_settings),
        consultant=ConsultantBehavior(consultant_adapter, consultant_context, consultant_settings),
        grouping_judge=GroupingJudgeBehavior(grouping_adapter, grouping_settings),
        architect=ArchitectBehavior(architect_adapter, architect_context, architect_settings),
        embedder=NodeEmbedder(embedder_port, embedder_settings),
        get_project_snapshot=_get_project_snapshot,
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
        apply_template_structure=_apply_template_structure,
        list_sections=_list_sections
    )

    return BackendOrchestratorRuntime(deps=deps, db=prisma, owns_db=owns_db)
