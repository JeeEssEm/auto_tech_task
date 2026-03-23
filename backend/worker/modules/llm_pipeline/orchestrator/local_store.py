from __future__ import annotations

import json
import re
from asyncio import Lock
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.schemas import DocumentSnapshot
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import (
    ArchitectResponse,
    ConsistencyCheckResult,
    ContextDetail,
    GKGFact,
    PendingAction,
    SourceChunk as ArchitectSourceChunk,
    WrittenSection,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.schemas import (
    GKGNodeDetail,
    GKGSearchResult,
    SourceChunk as ConsultantSourceChunk,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.context import ProjectSnapshot
from backend.worker.modules.llm_pipeline.steps.behaviors.grouping_judge.schemas import GKGNode, PendingConflict
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.staging import StagingNode
from backend.worker.modules.llm_pipeline.steps.embedder.schemas import EmbeddedStagingNode


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _score(query: str, candidate: str) -> float:
    q = Counter(_tokenize(query))
    c = Counter(_tokenize(candidate))
    if not q:
        return 0.0
    overlap = sum((q & c).values())
    return overlap / sum(q.values())


@dataclass
class LocalJSONGraphStore:
    state_path: Path

    def __post_init__(self) -> None:
        self._lock = Lock()
        self._state: dict[str, Any] = {"projects": {}}

    async def load(self) -> None:
        async with self._lock:
            if not self.state_path.exists():
                self.state_path.parent.mkdir(parents=True, exist_ok=True)
                await self._flush_locked()
                return
            self._state = json.loads(self.state_path.read_text(encoding="utf-8"))

    async def _flush_locked(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(self._state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _ensure_project_locked(self, project_id: int) -> dict[str, Any]:
        key = str(project_id)
        projects = self._state.setdefault("projects", {})
        project = projects.get(key)
        if project is not None:
            return project

        project = {
            "gkg_nodes": [],
            "pending_conflicts": [],
            "pending_actions": [],
            "raw_sources": [],
            "sections": {
                "sec_overview": {
                    "section_id": "sec_overview",
                    "title": "Общее описание проекта",
                    "level": 1,
                    "required": True,
                    "context_hint": "Общие цели, ограничения и контекст проекта",
                    "content_md": "",
                    "updated_at": datetime.now(UTC).isoformat(),
                },
                "sec_requirements": {
                    "section_id": "sec_requirements",
                    "title": "Функциональные требования",
                    "level": 1,
                    "required": True,
                    "context_hint": "Функциональные требования, сценарии, роли",
                    "content_md": "",
                    "updated_at": datetime.now(UTC).isoformat(),
                },
                "sec_architecture": {
                    "section_id": "sec_architecture",
                    "title": "Архитектура и технологии",
                    "level": 1,
                    "required": True,
                    "context_hint": "Архитектура, стек, инфраструктура, интеграции",
                    "content_md": "",
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            },
        }
        projects[key] = project
        return project

    async def capture_raw_source(
        self,
        project_id: int,
        source_id: str,
        source_name: str,
        text: str,
    ) -> None:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            project["raw_sources"].append(
                {
                    "source_id": source_id,
                    "source_name": source_name,
                    "chunk_index": len(project["raw_sources"]),
                    "text": text,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
            await self._flush_locked()

    async def persist_gkg(
        self,
        project_id: int,
        gkg_nodes: list[GKGNode],
        pending_conflicts: list[PendingConflict],
    ) -> None:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            by_id = {n["id"]: n for n in project["gkg_nodes"]}
            for node in gkg_nodes:
                by_id[node.id] = node.model_dump(mode="json")
            project["gkg_nodes"] = list(by_id.values())
            project["pending_conflicts"] = [c.model_dump(mode="json") for c in pending_conflicts]
            await self._flush_locked()

    async def get_existing_embedded_nodes(
        self,
        project_id: int,
        pairs: set[tuple[str, str]],
    ) -> list[EmbeddedStagingNode]:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            out: list[EmbeddedStagingNode] = []
            for raw in project["gkg_nodes"]:
                node = GKGNode.model_validate(raw)
                if (node.scope, node.property) not in pairs:
                    continue
                staging = StagingNode(
                    source_id=node.source_ids[0] if node.source_ids else "unknown",
                    scope=node.scope,
                    property=node.property,
                    value=node.value,
                    content_raw=node.content_raw,
                    author=None,
                    timestamp=None,
                    chunk_index=0,
                )
                out.append(EmbeddedStagingNode(node=staging, embedding=node.embedding))
            return out

    async def get_project_snapshot(self, project_id: int) -> ProjectSnapshot:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            gkg_nodes = [GKGNode.model_validate(n) for n in project["gkg_nodes"]]
            by_scope = Counter(node.scope for node in gkg_nodes)
            sections = list(project["sections"].values())
            return ProjectSnapshot(
                project_name=f"project-{project_id}",
                project_type="TZ generation",
                total_gkg_nodes=len(gkg_nodes),
                unresolved_conflicts=len(project["pending_conflicts"]),
                doc_section_titles=[s["title"] for s in sections],
                top_scopes=[scope for scope, _ in by_scope.most_common(10)],
            )

    async def get_gkg_snapshot_text(self, project_id: int) -> str:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            lines: list[str] = []
            for raw in project["gkg_nodes"]:
                node = GKGNode.model_validate(raw)
                lines.append(f"- [{node.status}] {node.scope} / {node.property}: {node.value}")
            return "\n".join(lines) if lines else "GKG is empty"

    # async def get_doc_snapshot_text(self, project_id: int) -> str:
    #     async with self._lock:
    #         project = self._ensure_project_locked(project_id)
    #         sections = sorted(project["sections"].values(), key=lambda s: (s["level"], s["section_id"]))
    #         lines: list[str] = []
    #         for sec in sections:
    #             content = sec.get("content_md", "")
    #             lines.append(f"- {sec['title']} (len={len(content)})")
    #         return "\n".join(lines) if lines else "Document is empty"

    async def get_doc_snapshot_text(self, project_id: int) -> str:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            sections = sorted(
                project["sections"].values(),
                key=lambda s: (s["level"], s["section_id"]),
            )
            lines: list[str] = []
            for sec in sections:
                content = sec.get("content_md", "")
                lines.append(f"- [{sec['section_id']}] {sec['title']} (len={len(content)})")
            return "\n".join(lines) if lines else "Document is empty"

    async def get_pending_action_questions(self, project_id: int) -> list[str]:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            return [a["question"] for a in project["pending_actions"] if a.get("status") == "WAITING"]

    async def export_gkg(self, project_id: int, out_path: Path) -> int:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            payload = {
                "project_id": project_id,
                "exported_at": datetime.now(UTC).isoformat(),
                "gkg_nodes": project["gkg_nodes"],
                "pending_conflicts": project["pending_conflicts"],
            }
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return len(project["gkg_nodes"])

    async def import_gkg(self, project_id: int, in_path: Path, merge: bool = True) -> int:
        payload = json.loads(in_path.read_text(encoding="utf-8"))
        raw_nodes = payload.get("gkg_nodes", [])
        raw_conflicts = payload.get("pending_conflicts", [])

        nodes = [GKGNode.model_validate(item) for item in raw_nodes]
        conflicts = [PendingConflict.model_validate(item) for item in raw_conflicts]

        async with self._lock:
            project = self._ensure_project_locked(project_id)
            if merge:
                by_id = {n["id"]: n for n in project["gkg_nodes"]}
                for node in nodes:
                    by_id[node.id] = node.model_dump(mode="json")
                project["gkg_nodes"] = list(by_id.values())
            else:
                project["gkg_nodes"] = [node.model_dump(mode="json") for node in nodes]

            project["pending_conflicts"] = [conflict.model_dump(mode="json") for conflict in conflicts]
            await self._flush_locked()
            return len(nodes)

    def _section_for_scope_locked(self, project: dict[str, Any], scope: str) -> dict[str, Any]:
        scope_norm = scope.lower().strip()
        if any(x in scope_norm for x in ("backend", "api", "db", "database", "infra")):
            key = "sec_architecture"
        elif any(x in scope_norm for x in ("role", "user", "functional", "feature", "frontend")):
            key = "sec_requirements"
        else:
            key = "sec_overview"

        if key not in project["sections"]:
            project["sections"][key] = {
                "section_id": key,
                "title": key.replace("sec_", "").replace("_", " ").title(),
                "level": 1,
                "required": True,
                "context_hint": f"Auto-created from scope: {scope}",
                "content_md": "",
                "updated_at": datetime.now(UTC).isoformat(),
            }
        return project["sections"][key]

    async def get_affected_sections(
        self,
        project_id: int,
        gkg_nodes: list[GKGNode],
    ) -> list[DocumentSnapshot]:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            if not gkg_nodes:
                return []

            selected_ids: set[str] = set()
            for node in gkg_nodes:
                sec = self._section_for_scope_locked(project, node.scope)
                selected_ids.add(sec["section_id"])

            all_gkg = [GKGNode.model_validate(n) for n in project["gkg_nodes"]]
            out: list[DocumentSnapshot] = []

            for sec_id in selected_ids:
                sec = project["sections"][sec_id]
                facts = [
                    GKGFact(
                        topic_id=n.id,
                        scope=n.scope,
                        property=n.property,
                        value=n.value,
                        status=n.status,
                        source_ids=n.source_ids,
                    )
                    for n in all_gkg
                    if self._section_for_scope_locked(project, n.scope)["section_id"] == sec_id
                ]
                written_sections = [
                    WrittenSection(
                        section_id=s["section_id"],
                        title=s["title"],
                        content_md=s.get("content_md", ""),
                    )
                    for s in project["sections"].values()
                    if s.get("content_md") and s["section_id"] != sec_id
                ]
                out.append(
                    DocumentSnapshot(
                        section_id=sec["section_id"],
                        section_title=sec["title"],
                        section_level=sec["level"],
                        section_required=sec["required"],
                        context_hint=sec["context_hint"],
                        trigger_reason="spec_block_affected",
                        section_facts=facts,
                        written_sections=written_sections,
                    )
                )

            await self._flush_locked()
            return out

    async def apply_document_updates(self, project_id: int, updates: list[ArchitectResponse]) -> None:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            for upd in updates:
                sec = project["sections"].get(upd.section_id)
                if sec is None:
                    sec = {
                        "section_id": upd.section_id,
                        "title": upd.section_id,
                        "level": 1,
                        "required": False,
                        "context_hint": "Auto-created by architect",
                        "content_md": "",
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                    project["sections"][upd.section_id] = sec
                if upd.status != "missing":
                    sec["content_md"] = upd.content_md
                sec["updated_at"] = datetime.now(UTC).isoformat()

                for action in upd.pending_actions:
                    project["pending_actions"].append(
                        {
                            "action_id": action.action_id,
                            "question": action.question,
                            "options": action.options,
                            "status": "WAITING",
                            "created_at": datetime.now(UTC).isoformat(),
                        }
                    )
            await self._flush_locked()

    async def create_pending_action(self, project_id: int, question: str, options: list[str] | None) -> str:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            action_id = str(uuid4())
            project["pending_actions"].append(
                {
                    "action_id": action_id,
                    "question": question,
                    "options": options,
                    "status": "WAITING",
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
            await self._flush_locked()
            return action_id

    async def resolve_pending_action(self, project_id: int, action_id: str, resolution: str) -> list[GKGNode]:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            found = None
            for action in project["pending_actions"]:
                if action["action_id"] == action_id and action.get("status") == "WAITING":
                    action["status"] = "RESOLVED"
                    action["resolution"] = resolution
                    found = action
                    break

            if found is None:
                return []

            node = GKGNode(
                scope="UserDecision",
                property=found["question"][:120],
                value=resolution,
                content_raw=resolution,
                status="RESOLVED",
                source_ids=[f"pending_action:{action_id}"],
                rationale="User resolved pending action",
                embedding=[0.0, 0.0, 0.0],
            )
            project["gkg_nodes"].append(node.model_dump(mode="json"))
            await self._flush_locked()
            return [node]

    async def mark_block_manual(self, project_id: int, block_id: str, content_md: str) -> None:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            sec = project["sections"].get(block_id)
            if sec is None:
                sec = {
                    "section_id": block_id,
                    "title": block_id,
                    "level": 1,
                    "required": False,
                    "context_hint": "Manual section",
                    "content_md": "",
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                project["sections"][block_id] = sec
            sec["content_md"] = content_md
            sec["manual"] = True
            sec["updated_at"] = datetime.now(UTC).isoformat()
            await self._flush_locked()

    async def build_document_snapshot(self, project_id: int, block_id: str, trigger_reason: str) -> DocumentSnapshot:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            sec = project["sections"].get(block_id)
            if sec is None:
                sec = {
                    "section_id": block_id,
                    "title": block_id,
                    "level": 1,
                    "required": False,
                    "context_hint": "User-requested custom section",
                    "content_md": "",
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                project["sections"][block_id] = sec

            all_gkg = [GKGNode.model_validate(n) for n in project["gkg_nodes"]]
            facts = [
                GKGFact(
                    topic_id=n.id,
                    scope=n.scope,
                    property=n.property,
                    value=n.value,
                    status=n.status,
                    source_ids=n.source_ids,
                )
                for n in all_gkg
            ]
            written_sections = [
                WrittenSection(
                    section_id=s["section_id"],
                    title=s["title"],
                    content_md=s.get("content_md", ""),
                )
                for s in project["sections"].values()
                if s.get("content_md") and s["section_id"] != block_id
            ]

            await self._flush_locked()
            return DocumentSnapshot(
                section_id=sec["section_id"],
                section_title=sec["title"],
                section_level=sec["level"],
                section_required=sec["required"],
                context_hint=sec["context_hint"],
                trigger_reason=trigger_reason,
                section_facts=facts,
                written_sections=written_sections,
            )

    async def consultant_search_gkg(self, project_id: int, query: str, limit: int) -> list[GKGSearchResult]:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            scored: list[tuple[float, GKGNode]] = []
            for raw in project["gkg_nodes"]:
                node = GKGNode.model_validate(raw)
                score = _score(query, f"{node.scope} {node.property} {node.value} {node.rationale} {node.content_raw}")
                if score > 0:
                    scored.append((score, node))
            scored.sort(key=lambda item: item[0], reverse=True)
            return [
                GKGSearchResult(
                    topic_id=node.id,
                    scope=node.scope,
                    property=node.property,
                    value=node.value,
                    status=node.status,
                    rationale=node.rationale,
                    source_ids=node.source_ids,
                    score=round(score_value, 4),
                )
                for score_value, node in scored[:limit]
            ]

    async def consultant_get_gkg_node_detail(self, project_id: int, topic_id: str) -> GKGNodeDetail | None:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            for raw in project["gkg_nodes"]:
                node = GKGNode.model_validate(raw)
                if node.id != topic_id:
                    continue
                return GKGNodeDetail(
                    topic_id=node.id,
                    scope=node.scope,
                    property=node.property,
                    winning_value=node.value,
                    rationale=node.rationale,
                    evidence=[
                        {
                            "quote": node.content_raw,
                            "author": "user",
                            "timestamp": "unknown",
                            "source_id": node.source_ids[0] if node.source_ids else "unknown",
                        }
                    ],
                    rejected_alternatives=[],
                )
            return None

    async def consultant_search_raw_sources(
        self,
        project_id: int,
        query: str,
        limit: int,
    ) -> list[ConsultantSourceChunk]:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            scored: list[tuple[float, dict[str, Any]]] = []
            for chunk in project["raw_sources"]:
                score = _score(query, chunk["text"])
                if score > 0:
                    scored.append((score, chunk))
            scored.sort(key=lambda item: item[0], reverse=True)
            return [
                ConsultantSourceChunk(
                    source_id=chunk["source_id"],
                    source_name=chunk["source_name"],
                    chunk_index=chunk["chunk_index"],
                    text=chunk["text"],
                    score=round(score_value, 4),
                )
                for score_value, chunk in scored[:limit]
            ]

    async def architect_get_context_details(self, project_id: int, topic_id: str) -> ContextDetail | None:
        detail = await self.consultant_get_gkg_node_detail(project_id, topic_id)
        if detail is None:
            return None
        return ContextDetail(
            topic_id=detail.topic_id,
            winning_value=detail.winning_value,
            rationale=detail.rationale,
            evidence=detail.evidence,
            rejected_alternatives=detail.rejected_alternatives,
        )

    async def architect_search_raw_sources(
        self,
        project_id: int,
        query: str,
        limit: int,
    ) -> list[ArchitectSourceChunk]:
        chunks = await self.consultant_search_raw_sources(project_id, query, limit)
        return [
            ArchitectSourceChunk(
                source_id=c.source_id,
                source_name=c.source_name,
                chunk_index=c.chunk_index,
                text=c.text,
                score=c.score,
            )
            for c in chunks
        ]

    async def architect_validate_consistency(
        self,
        draft_text: str,
        written_sections: list[WrittenSection],
    ) -> ConsistencyCheckResult:
        low = draft_text.lower()
        db_terms = ["postgres", "clickhouse", "mysql", "mongodb", "sqlite"]
        mentioned = {term for term in db_terms if term in low}
        if len(mentioned) <= 1:
            return ConsistencyCheckResult(status="OK", reason="")

        existing_text = " ".join(section.content_md.lower() for section in written_sections)
        existing_mentioned = {term for term in db_terms if term in existing_text}
        if existing_mentioned and not (mentioned & existing_mentioned):
            return ConsistencyCheckResult(
                status="CONFLICT",
                reason=f"Draft DB terms {sorted(mentioned)} contradict existing {sorted(existing_mentioned)}",
            )
        return ConsistencyCheckResult(status="OK", reason="")

    async def list_sections(self, project_id: int) -> list[tuple[str, str]]:
        async with self._lock:
            project = self._ensure_project_locked(project_id)
            return [
                (sec["section_id"], sec["title"])
                for sec in project["sections"].values()
            ]

    async def architect_search_gkg(
            self,
            project_id: int,
            query: str,
            limit: int,
    ) -> list[GKGSearchResult]:
        return await self.consultant_search_gkg(project_id, query, limit)
