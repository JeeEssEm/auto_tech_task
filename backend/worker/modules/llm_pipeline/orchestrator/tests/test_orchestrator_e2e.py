from __future__ import annotations

import pytest

from backend.worker.modules.llm_pipeline.orchestrator.nodes import OrchestratorDeps
from backend.worker.modules.llm_pipeline.orchestrator.orchestrator import Orchestrator
from backend.worker.modules.llm_pipeline.orchestrator.state import Attachment
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.context import ArchitectContext
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.schemas import DocumentSnapshot
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.architect_behavior import ArchitectBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.config import ArchitectSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import (
    ConsistencyCheckResult,
    ContextDetail,
    GKGFact,
    SourceChunk,
    WrittenSection,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.context import ConsultantContext
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.schemas import (
    GKGNodeDetail,
    GKGSearchResult,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.consultant_behavior import ConsultantBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.config import ConsultantSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.context import ProjectSnapshot
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.schemas import (
    GKGNode,
    GroupingJudgeResult,
    PendingConflict,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.guardian.guardian_behavior import GuardianBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.staging import StagingNode
from backend.worker.modules.llm_pipeline.steps.embedder.schemas import EmbeddedStagingNode
from backend.worker.modules.llm_pipeline.steps.intent_router.config import IntentRouterSettings
from backend.worker.modules.llm_pipeline.steps.intent_router.intent_router import IntentRouter
from backend.worker.modules.llm_pipeline.providers.configs.openai_settings import OpenAIChatSettings
from backend.worker.modules.llm_pipeline.providers.openai_adapter import OpenAIChatAdapter
from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import IntentRouterResponse
from backend.worker.modules.llm_pipeline.steps.shared.behaviours import (
    BehaviorReason,
    BehaviorRole,
    RouterBehavior,
)


class MinimalConsultantContext(ConsultantContext):
    async def search_gkg(self, query: str, limit: int = 5) -> list[GKGSearchResult]:
        return [
            GKGSearchResult(
                topic_id="backend_framework",
                scope="Backend",
                property="Framework",
                value="FastAPI",
                status="RESOLVED",
                rationale="Fast API development",
                source_ids=["chat-11"],
                score=0.93,
            )
        ]

    async def get_gkg_node_detail(self, topic_id: str) -> GKGNodeDetail | None:
        return GKGNodeDetail(
            topic_id=topic_id,
            scope="Backend",
            property="Framework",
            winning_value="FastAPI",
            rationale="Async API",
            evidence=[{"quote": "Используем FastAPI", "author": "team", "timestamp": "2026-03-22", "source_id": "chat-11"}],
            rejected_alternatives=[],
        )

    async def search_raw_sources(self, query: str, limit: int = 3) -> list[SourceChunk]:
        return [
            SourceChunk(
                source_id="chat-11",
                source_name="telegram_chat",
                chunk_index=1,
                text="Команда выбрала FastAPI для backend.",
                score=0.8,
            )
        ]


class MinimalArchitectContext(ArchitectContext):
    async def get_context_details(self, topic_id: str) -> ContextDetail | None:
        return ContextDetail(
            topic_id=topic_id,
            winning_value="FastAPI",
            rationale="Fast API development",
            evidence=[{"quote": "Берем FastAPI", "author": "team", "timestamp": "2026-03-22", "source_id": "chat-11"}],
            rejected_alternatives=[],
        )

    async def search_raw_sources(self, query: str, limit: int = 2) -> list[SourceChunk]:
        return [
            SourceChunk(
                source_id="chat-11",
                source_name="telegram_chat",
                chunk_index=1,
                text="Команда выбрала FastAPI для backend.",
                score=0.82,
            )
        ]

    async def ask_user(self, question: str, options: list[str] | None) -> str:
        return "e2e-action-1"

    async def validate_consistency(
        self,
        draft_text: str,
        written_sections: list[WrittenSection],
    ) -> ConsistencyCheckResult:
        return ConsistencyCheckResult(status="OK", reason="")


class FakeHarvester:
    async def process_source(self, source_id: str, text: str, source_meta: str) -> list[StagingNode]:
        return [
            StagingNode(
                source_id=source_id,
                scope="Backend",
                property="Framework",
                value="FastAPI",
                content_raw=text,
                author="user",
                timestamp="2026-03-22",
                chunk_index=0,
            )
        ]


class FakeEmbedder:
    async def execute(self, nodes: list[StagingNode]) -> list[EmbeddedStagingNode]:
        return [EmbeddedStagingNode(node=n, embedding=[0.1, 0.2, 0.3]) for n in nodes]


class FakeGroupingJudge:
    async def run(self, nodes: list[EmbeddedStagingNode]) -> GroupingJudgeResult:
        first = nodes[0]
        return GroupingJudgeResult(
            gkg_nodes=[
                GKGNode(
                    scope=first.node.scope,
                    property=first.node.property,
                    value=first.node.value,
                    content_raw=first.node.content_raw,
                    status="NO_CONFLICT",
                    source_ids=[first.node.source_id],
                    rationale="e2e-judge",
                    embedding=first.embedding,
                )
            ],
            pending_conflicts=[],
        )


class FakePersist:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, project_id: int, nodes: list[GKGNode], conflicts: list[PendingConflict]) -> None:
        self.calls += 1


class FakeIntentRouterHarvesterOnly:
    async def extract_behaviours(self, request):
        return IntentRouterResponse(
            behaviors=[
                RouterBehavior(
                    role=BehaviorRole.HARVESTER,
                    reason=BehaviorReason.NEW_FACT_DETECTED,
                    quote=request.user_prompt,
                )
            ]
        )


@pytest.fixture
def e2e_settings_bundle():
    try:
        return {
            "intent": IntentRouterSettings(),
            "consultant": ConsultantSettings(),
            "architect": ArchitectSettings(),
        }
    except Exception as e:
        pytest.skip(f"LLM settings are not configured for orchestrator e2e: {e}")


def _build_adapter(base_url: str, api_key: str | None, temperature: float, max_tokens: int, timeout_seconds: float, log_path: str):
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


def _base_callbacks(persist: FakePersist):
    async def get_project_snapshot(project_id: int) -> ProjectSnapshot:
        return ProjectSnapshot(
            project_name=f"project-{project_id}",
            project_type="TZ generation",
            total_gkg_nodes=3,
            unresolved_conflicts=0,
            doc_section_titles=["1. Intro", "2. Backend"],
            top_scopes=["Backend"],
        )

    async def get_affected_sections(project_id: int, gkg_nodes: list[GKGNode]) -> list[DocumentSnapshot]:
        if not gkg_nodes:
            return []
        return [
            DocumentSnapshot(
                section_id="sec_backend",
                section_title="Backend",
                section_level=2,
                section_required=True,
                context_hint="Backend framework",
                trigger_reason="spec_block_affected",
                section_facts=[
                    GKGFact(
                        topic_id="backend_framework",
                        scope="Backend",
                        property="Framework",
                        value="FastAPI",
                        status="RESOLVED",
                        source_ids=["chat-11"],
                    )
                ],
                written_sections=[
                    WrittenSection(
                        section_id="sec_intro",
                        title="Введение",
                        content_md="Проект backend ориентирован на API.",
                    )
                ],
            )
        ]

    async def load_existing_gkg_nodes(project_id: int, pairs: set[tuple[str, str]]) -> list[EmbeddedStagingNode]:
        return []

    async def get_gkg_snapshot(project_id: int) -> str:
        return "gkg snapshot"

    async def get_doc_snapshot(project_id: int) -> str:
        return "doc snapshot"

    async def get_pending_actions(project_id: int) -> list[str]:
        return []

    return {
        "get_project_snapshot": get_project_snapshot,
        "get_affected_sections": get_affected_sections,
        "persist_gkg": persist,
        "load_existing_gkg_nodes": load_existing_gkg_nodes,
        "get_gkg_snapshot": get_gkg_snapshot,
        "get_doc_snapshot": get_doc_snapshot,
        "get_pending_actions": get_pending_actions,
    }


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_orchestrator_e2e_guardian_path(e2e_settings_bundle):
    intent_s = e2e_settings_bundle["intent"]
    consultant_s = e2e_settings_bundle["consultant"]
    architect_s = e2e_settings_bundle["architect"]

    intent_adapter = _build_adapter(intent_s.base_url, intent_s.api_key, intent_s.temperature, intent_s.max_tokens, intent_s.timeout_seconds, "orchestrator_e2e_router.log")
    consultant_adapter = _build_adapter(consultant_s.base_url, consultant_s.api_key, consultant_s.temperature, consultant_s.max_tokens, consultant_s.timeout_seconds, "orchestrator_e2e_consultant.log")
    architect_adapter = _build_adapter(architect_s.base_url, architect_s.api_key, architect_s.temperature, architect_s.max_tokens, architect_s.timeout_seconds, "orchestrator_e2e_architect.log")

    persist = FakePersist()
    callbacks = _base_callbacks(persist)

    deps = OrchestratorDeps(
        intent_router=IntentRouter(intent_adapter, intent_s),
        guardian=GuardianBehavior(intent_adapter, intent_s),
        consultant=ConsultantBehavior(consultant_adapter, MinimalConsultantContext(), consultant_s),
        architect=ArchitectBehavior(architect_adapter, MinimalArchitectContext(), architect_s),
        harvester=FakeHarvester(),
        grouping_judge=FakeGroupingJudge(),
        embedder=FakeEmbedder(),
        architect_context=MinimalArchitectContext(),
        **callbacks,
    )

    orchestrator = Orchestrator(deps)

    result = await orchestrator.run(
        project_id=101,
        user_input="Напиши мне код быстрой сортировки на Python",
        attachments=[],
    )

    assert result.chat_text.strip()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_orchestrator_e2e_consultant_path(e2e_settings_bundle):
    intent_s = e2e_settings_bundle["intent"]
    consultant_s = e2e_settings_bundle["consultant"]
    architect_s = e2e_settings_bundle["architect"]

    intent_adapter = _build_adapter(intent_s.base_url, intent_s.api_key, intent_s.temperature, intent_s.max_tokens, intent_s.timeout_seconds, "orchestrator_e2e_router.log")
    consultant_adapter = _build_adapter(consultant_s.base_url, consultant_s.api_key, consultant_s.temperature, consultant_s.max_tokens, consultant_s.timeout_seconds, "orchestrator_e2e_consultant.log")
    architect_adapter = _build_adapter(architect_s.base_url, architect_s.api_key, architect_s.temperature, architect_s.max_tokens, architect_s.timeout_seconds, "orchestrator_e2e_architect.log")

    persist = FakePersist()
    callbacks = _base_callbacks(persist)

    deps = OrchestratorDeps(
        intent_router=IntentRouter(intent_adapter, intent_s),
        guardian=GuardianBehavior(intent_adapter, intent_s),
        consultant=ConsultantBehavior(consultant_adapter, MinimalConsultantContext(), consultant_s),
        architect=ArchitectBehavior(architect_adapter, MinimalArchitectContext(), architect_s),
        harvester=FakeHarvester(),
        grouping_judge=FakeGroupingJudge(),
        embedder=FakeEmbedder(),
        architect_context=MinimalArchitectContext(),
        **callbacks,
    )

    orchestrator = Orchestrator(deps)

    result = await orchestrator.run(
        project_id=102,
        user_input="Какие у нас требования к backend API и почему выбран FastAPI?",
        attachments=[],
    )

    assert result.chat_text.strip()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_orchestrator_e2e_full_harvester_architect_flow_with_real_architect(e2e_settings_bundle):
    intent_s = e2e_settings_bundle["intent"]
    consultant_s = e2e_settings_bundle["consultant"]
    architect_s = e2e_settings_bundle["architect"]

    intent_adapter = _build_adapter(intent_s.base_url, intent_s.api_key, intent_s.temperature, intent_s.max_tokens, intent_s.timeout_seconds, "orchestrator_e2e_router.log")
    consultant_adapter = _build_adapter(consultant_s.base_url, consultant_s.api_key, consultant_s.temperature, consultant_s.max_tokens, consultant_s.timeout_seconds, "orchestrator_e2e_consultant.log")
    architect_adapter = _build_adapter(architect_s.base_url, architect_s.api_key, architect_s.temperature, architect_s.max_tokens, architect_s.timeout_seconds, "orchestrator_e2e_architect.log")

    persist = FakePersist()
    callbacks = _base_callbacks(persist)

    deps = OrchestratorDeps(
        intent_router=FakeIntentRouterHarvesterOnly(),
        guardian=GuardianBehavior(intent_adapter, intent_s),
        consultant=ConsultantBehavior(consultant_adapter, MinimalConsultantContext(), consultant_s),
        architect=ArchitectBehavior(architect_adapter, MinimalArchitectContext(), architect_s),
        harvester=FakeHarvester(),
        grouping_judge=FakeGroupingJudge(),
        embedder=FakeEmbedder(),
        architect_context=MinimalArchitectContext(),
        **callbacks,
    )

    orchestrator = Orchestrator(deps)

    attachments: list[Attachment] = [
        {"source_id": "f-1", "name": "notes.txt", "text": "Новый факт: backend FastAPI"}
    ]
    result = await orchestrator.run(
        project_id=103,
        user_input="Добавляю новый факт для ТЗ: backend на FastAPI",
        attachments=attachments,
    )

    assert persist.calls == 1
    assert len(result.doc_updates) >= 1
    assert "Обновил разделы ТЗ" in result.chat_text
