from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.worker.modules.llm_pipeline.orchestrator.nodes import (
    OrchestratorDeps,
    fan_out,
)
from backend.worker.modules.llm_pipeline.orchestrator.orchestrator import Orchestrator
from backend.worker.modules.llm_pipeline.orchestrator.state import Attachment
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.schemas import (
    DocumentSnapshot,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import (
    ArchitectResponse,
    GKGFact,
    PendingAction,
    WrittenSection,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.schemas import (
    GKGNodeDetail,
    GKGSearchResult,
    SourceChunk,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.context import ProjectSnapshot
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.schemas import (
    ConsultantResponse,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.schemas import (
    GKGNode,
    GroupingJudgeResult,
    PendingConflict,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.guardian.guardian_behavior import (
    GuardianResponse,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.staging import StagingNode
from backend.worker.modules.llm_pipeline.steps.embedder.schemas import EmbeddedStagingNode
from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import (
    IntentRouterRequest,
    IntentRouterResponse,
)
from backend.worker.modules.llm_pipeline.steps.shared.behaviours import (
    BehaviorReason,
    BehaviorRole,
    RouterBehavior,
)


class FakeIntentRouter:
    async def extract_behaviours(self, request: IntentRouterRequest) -> IntentRouterResponse:
        prompt = request.user_prompt.lower()
        behaviors: list[RouterBehavior] = []

        if "guardian" in prompt or "сортиров" in prompt:
            behaviors.append(
                RouterBehavior(
                    role=BehaviorRole.GUARDIAN,
                    reason=BehaviorReason.OFFTOPIC_SEGMENT,
                    quote=request.user_prompt,
                )
            )
        if "consult" in prompt or "какие" in prompt:
            behaviors.append(
                RouterBehavior(
                    role=BehaviorRole.CONSULTANT,
                    reason=BehaviorReason.QUESTION_ABOUT_PROJECT,
                    quote=request.user_prompt,
                )
            )
        if "harvest" in prompt or "новый факт" in prompt:
            behaviors.append(
                RouterBehavior(
                    role=BehaviorRole.HARVESTER,
                    reason=BehaviorReason.NEW_FACT_DETECTED,
                    quote=request.user_prompt,
                )
            )
        if "regen" in prompt:
            behaviors.append(
                RouterBehavior(
                    role=BehaviorRole.ARCHITECT,
                    reason=BehaviorReason.EXPLICIT_REGEN_REQUEST,
                    quote=request.user_prompt,
                )
            )

        return IntentRouterResponse(behaviors=behaviors)


class FakeGuardian:
    async def run(self, **kwargs) -> GuardianResponse:
        return GuardianResponse(message="[guardian] запрос вне контура")


class FakeConsultant:
    async def run(self, **kwargs) -> ConsultantResponse:
        return ConsultantResponse(
            answer="[consultant] ответ по проекту",
            used_tool_calls=1,
            source_refs=["topic-1"],
        )


class FakeHarvester:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def process_source(self, source_id: str, text: str, source_meta: str) -> list[StagingNode]:
        self.calls.append((source_id, text, source_meta))
        if "empty" in text.lower():
            return []
        return [
            StagingNode(
                source_id=source_id,
                scope="Backend",
                property="Framework",
                value="FastAPI",
                content_raw=text,
                author="user",
                timestamp="2026-03-22T10:00:00Z",
                chunk_index=0,
            )
        ]


class FakeEmbedder:
    async def execute(self, nodes: list[StagingNode]) -> list[EmbeddedStagingNode]:
        return [EmbeddedStagingNode(node=n, embedding=[0.1, 0.2, 0.3]) for n in nodes]


class FakeGroupingJudge:
    async def run(self, nodes: list[EmbeddedStagingNode]) -> GroupingJudgeResult:
        if not nodes:
            return GroupingJudgeResult(gkg_nodes=[], pending_conflicts=[])

        first = nodes[0]
        conflict = any("conflict" in n.node.content_raw.lower() for n in nodes)
        pending = []
        if conflict:
            pending.append(
                PendingConflict(
                    scope=first.node.scope,
                    property=first.node.property,
                    options=[first],
                    rationale="manual resolution required",
                )
            )

        return GroupingJudgeResult(
            gkg_nodes=[
                GKGNode(
                    scope=first.node.scope,
                    property=first.node.property,
                    value=first.node.value,
                    content_raw=first.node.content_raw,
                    status="NO_CONFLICT",
                    source_ids=[first.node.source_id],
                    rationale="mocked-judge",
                    embedding=first.embedding,
                )
            ],
            pending_conflicts=pending,
        )


class FakeArchitect:
    async def run(self, snapshot: DocumentSnapshot) -> ArchitectResponse:
        if snapshot.section_required and not snapshot.section_facts:
            return ArchitectResponse(
                section_id=snapshot.section_id,
                content_md="",
                status="missing",
                pending_actions=[PendingAction(action_id="a-1", question="Уточните данные", options=None)],
                used_tool_calls=1,
            )
        return ArchitectResponse(
            section_id=snapshot.section_id,
            content_md="### Секция\n\nСгенерировано мок-архитектором.",
            status="generated",
            pending_actions=[],
            used_tool_calls=2,
        )


@dataclass
class MockCallbacks:
    persisted_calls: int = 0

    async def get_project_snapshot(self, project_id: int) -> ProjectSnapshot:
        return ProjectSnapshot(
            project_name=f"project-{project_id}",
            project_type="TZ generation",
            total_gkg_nodes=2,
            unresolved_conflicts=0,
            doc_section_titles=["1. Intro", "2. Tech"],
            top_scopes=["Backend", "API"],
        )

    async def get_affected_sections(self, project_id: int, gkg_nodes: list[GKGNode]) -> list[DocumentSnapshot]:
        if not gkg_nodes:
            return []
        return [
            DocumentSnapshot(
                section_id="sec_tech",
                section_title="Технологии",
                section_level=2,
                section_required=True,
                context_hint="Framework and DB",
                trigger_reason="spec_block_affected",
                section_facts=[
                    GKGFact(
                        topic_id="topic_backend_fw",
                        scope="Backend",
                        property="Framework",
                        value="FastAPI",
                        status="RESOLVED",
                        source_ids=["chat-1"],
                    )
                ],
                written_sections=[
                    WrittenSection(
                        section_id="sec_intro",
                        title="Введение",
                        content_md="Проект backend на Python.",
                    )
                ],
            )
        ]

    async def persist_gkg(self, project_id: int, nodes: list[GKGNode], conflicts: list[PendingConflict]) -> None:
        self.persisted_calls += 1

    async def load_existing_gkg_nodes(
        self,
        project_id: int,
        pairs: set[tuple[str, str]],
    ) -> list[EmbeddedStagingNode]:
        return []

    async def get_gkg_snapshot(self, project_id: int) -> str:
        return "mock-gkg-snapshot"

    async def get_doc_snapshot(self, project_id: int) -> str:
        return "mock-doc-snapshot"

    async def get_pending_actions(self, project_id: int) -> list[str]:
        return []


def _build_mock_deps(callbacks: MockCallbacks, harvester: FakeHarvester | None = None) -> OrchestratorDeps:
    return OrchestratorDeps(
        intent_router=FakeIntentRouter(),
        guardian=FakeGuardian(),
        harvester=harvester or FakeHarvester(),
        consultant=FakeConsultant(),
        grouping_judge=FakeGroupingJudge(),
        architect=FakeArchitect(),
        embedder=FakeEmbedder(),
        architect_context=None,
        get_project_snapshot=callbacks.get_project_snapshot,
        get_affected_sections=callbacks.get_affected_sections,
        persist_gkg=callbacks.persist_gkg,
        load_existing_gkg_nodes=callbacks.load_existing_gkg_nodes,
        get_gkg_snapshot=callbacks.get_gkg_snapshot,
        get_doc_snapshot=callbacks.get_doc_snapshot,
        get_pending_actions=callbacks.get_pending_actions,
    )


def test_fan_out_returns_compose_when_no_behaviors():
    sends = fan_out({"behaviors": []})
    assert len(sends) == 1
    assert sends[0].node == "compose_node"


def test_fan_out_returns_expected_nodes_for_mixed_behaviors():
    behaviors = [
        RouterBehavior(role=BehaviorRole.GUARDIAN, reason=BehaviorReason.OFFTOPIC_SEGMENT, quote="a"),
        RouterBehavior(role=BehaviorRole.CONSULTANT, reason=BehaviorReason.QUESTION_ABOUT_PROJECT, quote="b"),
        RouterBehavior(role=BehaviorRole.HARVESTER, reason=BehaviorReason.NEW_FACT_DETECTED, quote="c"),
    ]
    sends = fan_out({"behaviors": behaviors, "project_id": 1})
    nodes = {s.node for s in sends}
    assert "guardian_node" in nodes
    assert "consultant_node" in nodes
    assert "harvester_node" in nodes


@pytest.mark.asyncio
async def test_orchestrator_guardian_only_path():
    callbacks = MockCallbacks()
    deps = _build_mock_deps(callbacks)
    orchestrator = Orchestrator(deps)

    result = await orchestrator.run(
        project_id=1,
        user_input="guardian: напиши сортировку",
        attachments=[],
    )

    assert "[guardian]" in result.chat_text
    assert result.doc_updates == []


@pytest.mark.asyncio
async def test_orchestrator_consultant_only_path():
    callbacks = MockCallbacks()
    deps = _build_mock_deps(callbacks)
    orchestrator = Orchestrator(deps)

    result = await orchestrator.run(
        project_id=2,
        user_input="consult: какие требования к API?",
        attachments=[],
    )

    assert "[consultant]" in result.chat_text
    assert result.doc_updates == []


@pytest.mark.asyncio
async def test_orchestrator_harvester_to_architect_path_with_attachments():
    callbacks = MockCallbacks()
    harvester = FakeHarvester()
    deps = _build_mock_deps(callbacks, harvester=harvester)
    orchestrator = Orchestrator(deps)

    attachments: list[Attachment] = [
        {
            "source_id": "file-1",
            "name": "spec.txt",
            "text": "Новый факт: backend FastAPI",
        }
    ]

    result = await orchestrator.run(
        project_id=3,
        user_input="harvest: новый факт по архитектуре",
        attachments=attachments,
    )

    assert "Обновил разделы ТЗ" in result.chat_text
    assert len(result.doc_updates) == 1
    assert callbacks.persisted_calls == 1
    assert len(harvester.calls) >= 2  # attachment + user chat


@pytest.mark.asyncio
async def test_orchestrator_conflict_flow_returns_pending_conflicts():
    callbacks = MockCallbacks()
    deps = _build_mock_deps(callbacks)
    orchestrator = Orchestrator(deps)

    result = await orchestrator.run(
        project_id=4,
        user_input="harvest: conflict in db decision",
        attachments=[],
    )

    assert len(result.pending_conflicts) >= 1
    assert callbacks.persisted_calls == 1


@pytest.mark.asyncio
async def test_orchestrator_direct_architect_branch_without_snapshot_is_safe_noop():
    callbacks = MockCallbacks()
    deps = _build_mock_deps(callbacks)
    orchestrator = Orchestrator(deps)

    result = await orchestrator.run(
        project_id=5,
        user_input="regen: перепиши раздел технологий",
        attachments=[],
    )

    assert result.doc_updates == []
    assert result.chat_text.strip() == "Принято."


@pytest.mark.asyncio
async def test_orchestrator_mixed_path_compose_order():
    callbacks = MockCallbacks()
    deps = _build_mock_deps(callbacks)
    orchestrator = Orchestrator(deps)

    result = await orchestrator.run(
        project_id=6,
        user_input="guardian consult harvest: комбо запрос",
        attachments=[],
    )

    assert "[guardian]" in result.chat_text
    assert "[consultant]" in result.chat_text
    assert "Обновил разделы ТЗ" in result.chat_text
