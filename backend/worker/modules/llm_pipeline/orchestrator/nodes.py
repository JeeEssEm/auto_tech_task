"""
nodes.py — все узлы LangGraph-графа.

Каждый узел — async-функция (state) → dict с частичным обновлением State.
Узлы не знают друг о друге. Зависимости инжектируются через Dependencies-контейнер.

Порядок исполнения управляется рёбрами графа, не самими узлами.
"""

from dataclasses import dataclass
from typing import Callable, Awaitable
from datetime import datetime, UTC

import structlog
from langgraph.types import Send

from backend.worker.modules.llm_pipeline.orchestrator.state import (
    OrchestratorState, ArchitectNodeInput,
    GuardianNodeInput
)
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.context import ArchitectContext
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.schemas import DocumentSnapshot
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.architect_behavior import ArchitectBehavior

from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import ArchitectResponse
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.context import ConsultantContext
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.consultant_behavior import ConsultantBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.context import ProjectSnapshot

from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.schemas import GKGNode, PendingConflict
from backend.worker.modules.llm_pipeline.steps.behaviors.guardian.guardian_behavior import GuardianBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.judge import GroupingJudgeBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.harvester_behavior import HarvesterBehavior
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.staging import StagingNode
from backend.worker.modules.llm_pipeline.steps.embedder.node_embedder import NodeEmbedder
from backend.worker.modules.llm_pipeline.steps.embedder.schemas import EmbeddedStagingNode
from backend.worker.modules.llm_pipeline.steps.intent_router.intent_router import IntentRouter
from backend.worker.modules.llm_pipeline.steps.intent_router.schemas import IntentRouterRequest, AttachmentInfo
from backend.worker.modules.llm_pipeline.steps.shared.behaviours import BehaviorRole, BehaviorReason

log = structlog.get_logger(__name__)


@dataclass
class OrchestratorDeps:
    """
    Все behavior-объекты создаются один раз при старте приложения
    и инжектируются в узлы через замыкание (make_*_node-фабрики).

    Это позволяет:
    - Тестировать каждый узел с моками
    - Не пересоздавать HTTP-клиенты и модели при каждом запросе
    """
    intent_router: IntentRouter
    guardian: GuardianBehavior
    harvester: HarvesterBehavior
    consultant: ConsultantBehavior
    grouping_judge: GroupingJudgeBehavior
    architect: ArchitectBehavior
    embedder: NodeEmbedder

    # Колбэки для доступа к БД (реализуются на уровне API)
    get_project_snapshot: "Callable[[int], Awaitable[ProjectSnapshot]]"
    get_affected_sections: "Callable[[int, list[GKGNode]], Awaitable[list[DocumentSnapshot]]]"
    persist_gkg: "Callable[[int, list[GKGNode], list[PendingConflict]], Awaitable[None]]"
    load_existing_gkg_nodes: "Callable[[int, set[tuple[str, str]]], Awaitable[list[EmbeddedStagingNode]]]"

    get_gkg_snapshot: "Callable[[int], Awaitable[str]]"
    get_doc_snapshot: "Callable[[int], Awaitable[str]]"
    get_pending_actions: "Callable[[int], Awaitable[list[str]]]"

    consultant_context: ConsultantContext | None = None
    architect_context: ArchitectContext | None = None
    capture_raw_source: "Callable[[int, str, str, str], Awaitable[None]] | None" = None
    save_document_updates: "Callable[[int, list[ArchitectResponse]], Awaitable[None]] | None" = None
    build_document_snapshot: "Callable[[int, str, str], Awaitable[DocumentSnapshot]] | None" = None
    resolve_pending_action: "Callable[[int, str, str], Awaitable[list[GKGNode]]] | None" = None
    mark_block_manual: "Callable[[int, str, str], Awaitable[None]] | None" = None
    apply_template_structure: "Callable[[int, str], Awaitable[None]] | None" = None


def make_route_node(deps: OrchestratorDeps):
    async def route_node(state: OrchestratorState) -> dict:
        request = IntentRouterRequest(
            user_prompt=state["user_input"],
            attachments=[
                AttachmentInfo(file_name=a.get("name", "unknown"), truncated_content=a.get("text", "empty")[:50])
                for a in state.get("attachments", [])
            ],
            gkg_snapshot=state.get("gkg_snapshot"),
            doc_snapshot=state.get("doc_snapshot"),
            pending_actions=state.get("pending_actions", []),
        )
        result = await deps.intent_router.extract_behaviours(request)
        log.info(
            "route | project=%s behaviors=%s",
            state["project_id"],
            [b.role for b in result.behaviors],
        )
        return {"behaviors": result.behaviors}

    return route_node


def fan_out(state: OrchestratorState) -> list[Send]:
    """
    Conditional edge из route → возвращает список Send().

    Send(node_name, state_patch) — LangGraph запускает эти узлы параллельно,
    каждый получает полный State + патч как начальное состояние.

    Зависимость Architect от Harvester решается структурой графа:
    architect_gate стоит ПОСЛЕ grouping_judge, который стоит ПОСЛЕ harvester.
    Прямая активация Architect (explicit_regen_request без новых фактов)
    идёт отдельным путём — тоже через Send, но на другой узел.
    """
    sends: list[Send] = []
    behaviors = state.get("behaviors", [])

    roles = {b.role for b in behaviors}
    reasons = {b.reason for b in behaviors}

    if BehaviorRole.GUARDIAN in roles:
        guardian_behaviors = [b for b in behaviors if b.role == BehaviorRole.GUARDIAN]
        for b in guardian_behaviors:
            sends.append(
                Send(
                    "guardian_node", GuardianNodeInput(
                        project_id=state["project_id"],
                        guardian_behavior=b,
                    )
                )
            )

    if BehaviorRole.CONSULTANT in roles:
        sends.append(Send("consultant_node", state))

    if BehaviorRole.HARVESTER in roles:
        sends.append(Send("harvester_node", state))

    # Explicit regen без новых фактов — напрямую к архитектору
    if (
            BehaviorRole.ARCHITECT in roles
            and BehaviorReason.EXPLICIT_REGEN_REQUEST in reasons
            and BehaviorRole.HARVESTER not in roles
    ):
        architect_behaviors = [b for b in behaviors if b.role == BehaviorRole.ARCHITECT]
        for b in architect_behaviors:
            sends.append(Send("direct_architect_node", {**state, "_architect_quote": b.user_prompt}))

    # Если ни один behavior не подошёл — возвращаем пустой список,
    # граф сразу переходит к compose
    return sends or [Send("compose_node", state)]


def make_guardian_node(deps: OrchestratorDeps):
    async def guardian_node(state: GuardianNodeInput) -> dict:
        behavior = state.get("guardian_behavior")
        response = await deps.guardian.run(
            reason=behavior.reason,
            offending_input=behavior.user_prompt,
            project_name=f"project_{state['project_id']}",
            project_type="TZ generation",
        )
        return {"guardian_messages": [response.message]}

    return guardian_node


def make_consultant_node(deps: OrchestratorDeps):
    async def consultant_node(state: OrchestratorState) -> dict:
        if deps.consultant_context and hasattr(deps.consultant_context, "set_project_id"):
            deps.consultant_context.set_project_id(state["project_id"])

        snapshot = await deps.get_project_snapshot(state["project_id"])
        response = await deps.consultant.run(
            question=state["user_input"],
            snapshot=snapshot,
        )
        return {"consultant_responses": [response]}

    return consultant_node


def make_harvester_node(deps: OrchestratorDeps):
    async def harvester_node(state: OrchestratorState) -> dict:
        all_nodes: list[StagingNode] = []

        for attachment in state.get("attachments", []):
            if deps.capture_raw_source:
                await deps.capture_raw_source(
                    state["project_id"],
                    attachment["source_id"],
                    attachment["name"],
                    attachment["text"],
                )
            nodes = await deps.harvester.process_source(
                source_id=attachment["source_id"],
                text=attachment["text"],
                source_meta=attachment["name"],
            )
            all_nodes.extend(nodes)

        chat_nodes = await deps.harvester.process_source(
            source_id=f"user_chat_{state['project_id']}_{datetime.now(UTC).strftime('%Y-%m-%d_%H-%M')}",
            text=state["user_input"],
            source_meta="user_chat"
        )
        if deps.capture_raw_source:
            await deps.capture_raw_source(
                state["project_id"],
                f"user_chat_{state['project_id']}",
                "user_chat",
                state["user_input"],
            )
        all_nodes.extend(chat_nodes)

        return {"harvested_nodes": all_nodes}

    return harvester_node


def make_grouping_judge_node(deps: OrchestratorDeps):
    async def grouping_judge_node(state: OrchestratorState) -> dict:
        new_nodes = state.get("harvested_nodes", [])
        if not new_nodes:
            return {"gkg_nodes": [], "pending_conflicts": []}

        scope_property_pairs = {(n.scope, n.property) for n in new_nodes}
        existing_nodes = await deps.load_existing_gkg_nodes(
            state["project_id"],
            scope_property_pairs
        )

        embedded_new = await deps.embedder.execute(new_nodes)
        result = await deps.grouping_judge.run(existing_nodes + embedded_new)

        log.info(
            "grouping_judge | project=%s gkg_nodes=%d conflicts=%d",
            state["project_id"],
            len(result.gkg_nodes),
            len(result.pending_conflicts),
        )
        return {
            "gkg_nodes": result.gkg_nodes,
            "pending_conflicts": result.pending_conflicts,
        }

    return grouping_judge_node


def make_persist_gkg_node(deps: OrchestratorDeps):
    async def persist_gkg_node(state: OrchestratorState) -> dict:
        gkg_nodes = state.get("gkg_nodes", [])
        conflicts = state.get("pending_conflicts", [])
        if gkg_nodes or conflicts:
            await deps.persist_gkg(state["project_id"], gkg_nodes, conflicts)
        return {}

    return persist_gkg_node


def make_architect_gate(deps: OrchestratorDeps):
    async def architect_gate(state: OrchestratorState) -> list[Send]:
        """
        Conditional edge после persist_gkg.
        Если GKG обновился — находим затронутые секции и запускаем Architect
        параллельно для каждой через Send().
        """
        gkg_nodes = state.get("gkg_nodes", [])
        if not gkg_nodes:
            return [Send("compose_node", state)]

        snapshots: list[DocumentSnapshot] = await deps.get_affected_sections(
            state["project_id"], gkg_nodes
        )
        if not snapshots:
            return [Send("compose_node", state)]

        log.info(
            "architect_gate | project=%s affected_sections=%d",
            state["project_id"],
            len(snapshots),
        )
        return [
            Send(
                "architect_node", ArchitectNodeInput(
                    project_id=state["project_id"],
                    section_snapshot=snap,
                )
            )
            for snap in snapshots
        ]

    return architect_gate


def make_architect_node(deps: OrchestratorDeps):
    async def architect_node(state: ArchitectNodeInput) -> dict:
        if deps.architect_context and hasattr(deps.architect_context, "set_project_id"):
            deps.architect_context.set_project_id(state["project_id"])

        snapshot: DocumentSnapshot = state["section_snapshot"]
        response = await deps.architect.run(snapshot)
        log.info(
            "architect | section=%s status=%s tool_calls=%d",
            snapshot.section_id,
            response.status,
            response.used_tool_calls,
        )
        return {"architect_responses": [response]}

    return architect_node


def make_direct_architect_node(deps: OrchestratorDeps):
    async def direct_architect_node(state: ArchitectNodeInput) -> dict:
        if deps.architect_context and hasattr(deps.architect_context, "set_project_id"):
            deps.architect_context.set_project_id(state["project_id"])

        snapshot: DocumentSnapshot | None = state.get("section_snapshot")
        if snapshot is None:
            return {"architect_responses": []}

        response = await deps.architect.run(snapshot)
        return {"architect_responses": [response]}

    return direct_architect_node


def make_compose_node(_deps: OrchestratorDeps):
    async def compose_node(state: OrchestratorState) -> dict:
        """
        Собирает финальный ответ из всех частей.
        Порядок: Guardian → Consultant → уведомления об обновлениях ТЗ.
        """
        parts: list[str] = []

        for msg in state.get("guardian_messages", []):
            parts.append(msg)

        for resp in state.get("consultant_responses", []):
            parts.append(resp.answer)

        architect_responses = state.get("architect_responses", [])
        if architect_responses:
            updated = [r.section_id for r in architect_responses if r.status != "missing"]
            missing = [r.section_id for r in architect_responses if r.status == "missing"]
            if updated:
                parts.append(f"Обновил разделы ТЗ: {', '.join(updated)}.")
            if missing:
                parts.append(
                    f"Не хватает данных для разделов: {', '.join(missing)}. "
                    "Уточняющие вопросы добавлены."
                )

        if not parts:
            parts.append("Принято.")

        return {"chat_parts": parts}

    return compose_node
