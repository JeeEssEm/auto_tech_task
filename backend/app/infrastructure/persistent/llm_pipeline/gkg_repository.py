from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from prisma import Prisma

from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.schemas import DocumentSnapshot
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import (
    ArchitectResponse,
    ConsistencyCheckResult,
    ContextDetail,
    GKGFact,
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
from backend.worker.modules.llm_pipeline.templates.catalog import TEMPLATES
from backend.worker.modules.llm_pipeline.templates.template import TemplateBlock


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _score(query: str, candidate: str) -> float:
    q = Counter(_tokenize(query))
    c = Counter(_tokenize(candidate))
    if not q:
        return 0.0
    overlap = sum((q & c).values())
    return overlap / sum(q.values())


def _as_source_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            return [value]
    return []


def _template_alias(template_type: str) -> str:
    mapping = {
        "gost19": "formal_001",
        "free": "free_001",
        "it_project": "it_001",
        "construction_project": "construction_001",
        "engineering_project": "engineering_001",
        "formal": "formal_001",
        "it": "it_001",
        "construction": "construction_001",
        "engineering": "engineering_001",
    }
    key = (template_type or "").strip().lower()
    if key in TEMPLATES:
        return key
    resolved = mapping.get(key)
    if resolved is None:
        raise ValueError(f"Unknown template type: {template_type}")
    return resolved


def _flatten_template_blocks(blocks: list[TemplateBlock]) -> list[TemplateBlock]:
    out: list[TemplateBlock] = []
    for block in sorted(blocks, key=lambda item: item.sort_order):
        out.append(block)
        if block.subsections:
            out.extend(_flatten_template_blocks(block.subsections))
    return out


def _to_pgvector_literal(values: list[float]) -> str:
    if not values:
        return "[]"
    return "[" + ",".join(f"{float(v):.10f}" for v in values) + "]"


def _parse_pgvector_text(value: str | None) -> list[float]:
    if not value:
        return []
    raw = value.strip().strip("[]")
    if not raw:
        return []
    out: list[float] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(float(part))
        except ValueError:
            continue
    return out


class GKGRepository:
    def __init__(self, db: Prisma):
        self._db = db

    async def _set_embedding_vector(self, fact_id: str, embedding: list[float]) -> None:
        execute_raw = getattr(self._db, "execute_raw", None)
        if not callable(execute_raw) or not embedding:
            return
        vector = _to_pgvector_literal(embedding)
        # NOTE: use explicit cast to pgvector type
        await execute_raw(
            f"UPDATE \"LlmGkgFact\" SET embedding_vector = '{vector}'::vector WHERE id = '{fact_id}'::uuid"
        )

    async def apply_template_sections(self, project_id: int, template_type: str) -> None:
        template_id = _template_alias(template_type)
        template = TEMPLATES[template_id]
        blocks = _flatten_template_blocks(template.blocks)

        # Keep manual sections intact; reset generated sections to the selected template.
        await self._db.llmdocumentsection.delete_many(
            where={"project_id": project_id, "is_manual": False}
        )

        for index, block in enumerate(blocks):
            await self._db.llmdocumentsection.create(
                data={
                    "project_id": project_id,
                    "section_id": block.template_block_id,
                    "title": block.title,
                    "level": int(block.level),
                    "required": bool(block.required),
                    "context_hint": block.context_hint,
                    "content_md": "",
                    "is_manual": False,
                }
            )

    async def build_tz_result_payload(self, project_id: int, template_type: str | None = None) -> dict[str, Any]:
        await self._ensure_default_sections(project_id)
        sections = await self._db.llmdocumentsection.find_many(where={"project_id": project_id})

        section_map: dict[str, str] = {
            "general": "",
            "functional": "",
            "ui_ux": "",
            "technical": "",
            "non_functional": "",
            "stages": "",
            "acceptance": "",
        }

        for sec in sections:
            sid = (sec.section_id or "").lower()
            title = (sec.title or "").lower()
            hint = (sec.context_hint or "").lower()
            text = sec.content_md or ""

            if sid in {"sec_overview", "it_intro", "f_general", "fr_what", "c_object", "e_scope"}:
                section_map["general"] += ("\n\n" + text if section_map["general"] and text else text)
            elif sid in {"sec_requirements", "it_func", "f_requirements"}:
                section_map["functional"] += ("\n\n" + text if section_map["functional"] and text else text)
            elif sid in {"sec_architecture", "it_tech", "c_materials", "e_tech"}:
                section_map["technical"] += ("\n\n" + text if section_map["technical"] and text else text)
            elif "accept" in sid or "прием" in title:
                section_map["acceptance"] += ("\n\n" + text if section_map["acceptance"] and text else text)
            elif "stage" in sid or "этап" in title or "timeline" in sid:
                section_map["stages"] += ("\n\n" + text if section_map["stages"] and text else text)
            elif "ui" in sid or "ux" in sid or "интерф" in title:
                section_map["ui_ux"] += ("\n\n" + text if section_map["ui_ux"] and text else text)
            elif "non" in sid or "безопас" in title or "security" in hint or "performance" in hint:
                section_map["non_functional"] += ("\n\n" + text if section_map["non_functional"] and text else text)
            else:
                section_map["general"] += ("\n\n" + text if section_map["general"] and text else text)

        return {
            "template_type": template_type or "free",
            "document": section_map,
            "validation": {
                "is_complete": any(bool(value.strip()) for value in section_map.values()),
                "gaps": [],
                "conflicts": [],
                "completeness_percent": int(
                    (sum(1 for value in section_map.values() if value.strip()) / max(len(section_map), 1)) * 100
                ),
                "total_fields": len(section_map),
                "filled_fields": sum(1 for value in section_map.values() if value.strip()),
            },
            "custom_sections": {},
        }

    async def _ensure_default_sections(self, project_id: int) -> None:
        rows = await self._db.llmdocumentsection.find_many(where={"project_id": project_id})
        if rows:
            return

        defaults = [
            {
                "section_id": "sec_overview",
                "title": "Общее описание проекта",
                "level": 1,
                "required": True,
                "context_hint": "Общие цели, ограничения и контекст проекта",
            },
            {
                "section_id": "sec_requirements",
                "title": "Функциональные требования",
                "level": 1,
                "required": True,
                "context_hint": "Функциональные требования, сценарии, роли",
            },
            {
                "section_id": "sec_architecture",
                "title": "Архитектура и технологии",
                "level": 1,
                "required": True,
                "context_hint": "Архитектура, стек, инфраструктура, интеграции",
            },
        ]
        for row in defaults:
            await self._db.llmdocumentsection.create(
                data={
                    "project_id": project_id,
                    **row,
                    "content_md": "",
                    "is_manual": False,
                }
            )

    async def capture_raw_source(
        self,
        project_id: int,
        source_id: str,
        source_name: str,
        text: str,
    ) -> None:
        existing_count = await self._db.llmrawsourcechunk.count(
            where={"project_id": project_id, "source_id": source_id}
        )
        await self._db.llmrawsourcechunk.create(
            data={
                "project_id": project_id,
                "source_id": source_id,
                "source_name": source_name,
                "chunk_index": existing_count,
                "text": text,
            }
        )

    async def persist_gkg(
        self,
        project_id: int,
        gkg_nodes: list[GKGNode],
        pending_conflicts: list[PendingConflict],
    ) -> None:
        for node in gkg_nodes:
            existing = await self._db.llmgkgfact.find_first(
                where={"id": node.id, "project_id": project_id}
            )
            payload = {
                "project_id": project_id,
                "scope": node.scope,
                "property": node.property,
                "value": node.value,
                "content_raw": node.content_raw,
                "status": node.status,
                "rationale": node.rationale,
                "source_ids": json.dumps(node.source_ids),
            }
            if existing is None:
                await self._db.llmgkgfact.create(data={"id": node.id, **payload})
            else:
                await self._db.llmgkgfact.update(where={"id": node.id}, data=payload)
            await self._set_embedding_vector(node.id, node.embedding)

        await self._db.llmpendingconflict.delete_many(where={"project_id": project_id})
        for conflict in pending_conflicts:
            await self._db.llmpendingconflict.create(
                data={
                    "id": conflict.id,
                    "project_id": project_id,
                    "scope": conflict.scope,
                    "property": conflict.property,
                    "rationale": conflict.rationale,
                    "options_json": [opt.model_dump(mode="json") for opt in conflict.options],
                }
            )

    async def add_gkg_nodes(self, project_id: int, gkg_nodes: list[GKGNode]) -> None:
        if not gkg_nodes:
            return
        await self.persist_gkg(project_id, gkg_nodes, await self.get_pending_conflicts(project_id))

    async def get_pending_conflicts(self, project_id: int) -> list[PendingConflict]:
        rows = await self._db.llmpendingconflict.find_many(where={"project_id": project_id})
        out: list[PendingConflict] = []
        for row in rows:
            options = [EmbeddedStagingNode.model_validate(item) for item in (row.options_json or [])]
            out.append(
                PendingConflict(
                    id=row.id,
                    scope=row.scope,
                    property=row.property,
                    options=options,
                    rationale=row.rationale,
                )
            )
        return out

    async def get_existing_embedded_nodes(
        self,
        project_id: int,
        pairs: set[tuple[str, str]],
    ) -> list[EmbeddedStagingNode]:
        rows = await self._db.llmgkgfact.find_many(where={"project_id": project_id})
        out: list[EmbeddedStagingNode] = []
        for row in rows:
            if (row.scope, row.property) not in pairs:
                continue
            source_ids = _as_source_ids(row.source_ids)
            embedding = list(getattr(row, "embedding", []) or [])
            if not embedding:
                query_raw = getattr(self._db, "query_raw", None)
                if callable(query_raw):
                    try:
                        raw_rows = await query_raw(
                            f"SELECT embedding_vector::text AS embedding_text FROM \"LlmGkgFact\" WHERE id = '{row.id}'::uuid"
                        )
                        if raw_rows:
                            embedding = _parse_pgvector_text(str(raw_rows[0].get("embedding_text") or ""))
                    except Exception:
                        embedding = []
            staging = StagingNode(
                source_id=source_ids[0] if source_ids else "unknown",
                scope=row.scope,
                property=row.property,
                value=row.value,
                content_raw=row.content_raw,
                author=None,
                timestamp=None,
                chunk_index=0,
            )
            out.append(EmbeddedStagingNode(node=staging, embedding=embedding))
        return out

    async def get_project_snapshot(self, project_id: int) -> ProjectSnapshot:
        await self._ensure_default_sections(project_id)
        gkg_nodes = await self._db.llmgkgfact.find_many(where={"project_id": project_id})
        conflicts_count = await self._db.llmpendingconflict.count(where={"project_id": project_id})
        sections = await self._db.llmdocumentsection.find_many(where={"project_id": project_id})

        by_scope = Counter(row.scope for row in gkg_nodes)
        return ProjectSnapshot(
            project_name=f"project-{project_id}",
            project_type="TZ generation",
            total_gkg_nodes=len(gkg_nodes),
            unresolved_conflicts=conflicts_count,
            doc_section_titles=[row.title for row in sections],
            top_scopes=[scope for scope, _ in by_scope.most_common(10)],
        )

    async def get_gkg_snapshot_text(self, project_id: int) -> str:
        rows = await self._db.llmgkgfact.find_many(where={"project_id": project_id})
        lines = [f"- [{row.status}] {row.scope} / {row.property}: {row.value}" for row in rows]
        return "\n".join(lines) if lines else "GKG is empty"

    async def get_doc_snapshot_text(self, project_id: int) -> str:
        await self._ensure_default_sections(project_id)
        rows = await self._db.llmdocumentsection.find_many(where={"project_id": project_id})
        rows = sorted(rows, key=lambda s: (s.level, s.section_id))
        lines = [f"- {row.title} (len={len(row.content_md or '')})" for row in rows]
        return "\n".join(lines) if lines else "Document is empty"

    def _section_key_for_scope(self, scope: str) -> str:
        scope_norm = scope.lower().strip()
        if any(x in scope_norm for x in ("backend", "api", "db", "database", "infra")):
            return "sec_architecture"
        if any(x in scope_norm for x in ("role", "user", "functional", "feature", "frontend")):
            return "sec_requirements"
        return "sec_overview"

    async def _ensure_section(self, project_id: int, section_id: str, title: str | None = None) -> None:
        existing = await self._db.llmdocumentsection.find_first(
            where={"project_id": project_id, "section_id": section_id}
        )
        if existing is not None:
            return
        await self._db.llmdocumentsection.create(
            data={
                "project_id": project_id,
                "section_id": section_id,
                "title": title or section_id,
                "level": 1,
                "required": True,
                "context_hint": f"Auto-created from section: {section_id}",
                "content_md": "",
                "is_manual": False,
            }
        )

    async def get_affected_sections(
        self,
        project_id: int,
        gkg_nodes: list[GKGNode],
    ) -> list[DocumentSnapshot]:
        await self._ensure_default_sections(project_id)
        if not gkg_nodes:
            return []

        selected_ids = {self._section_key_for_scope(node.scope) for node in gkg_nodes}
        for sec_id in selected_ids:
            await self._ensure_section(project_id, sec_id)

        sections = await self._db.llmdocumentsection.find_many(where={"project_id": project_id})
        by_id = {row.section_id: row for row in sections}
        all_gkg = await self._db.llmgkgfact.find_many(where={"project_id": project_id})

        out: list[DocumentSnapshot] = []
        for sec_id in selected_ids:
            sec = by_id[sec_id]
            section_facts: list[GKGFact] = []
            for row in all_gkg:
                if self._section_key_for_scope(row.scope) != sec_id:
                    continue
                section_facts.append(
                    GKGFact(
                        topic_id=row.id,
                        scope=row.scope,
                        property=row.property,
                        value=row.value,
                        status=row.status,
                        source_ids=_as_source_ids(row.source_ids),
                    )
                )

            written_sections = [
                WrittenSection(
                    section_id=item.section_id,
                    title=item.title,
                    content_md=item.content_md or "",
                )
                for item in sections
                if (item.content_md or "") and item.section_id != sec_id
            ]

            out.append(
                DocumentSnapshot(
                    section_id=sec.section_id,
                    section_title=sec.title,
                    section_level=sec.level,
                    section_required=sec.required,
                    context_hint=sec.context_hint,
                    trigger_reason="spec_block_affected",
                    section_facts=section_facts,
                    written_sections=written_sections,
                )
            )
        return out

    async def apply_document_updates(self, project_id: int, updates: list[ArchitectResponse]) -> None:
        for upd in updates:
            existing = await self._db.llmdocumentsection.find_first(
                where={"project_id": project_id, "section_id": upd.section_id}
            )
            if existing is None:
                await self._db.llmdocumentsection.create(
                    data={
                        "project_id": project_id,
                        "section_id": upd.section_id,
                        "title": upd.section_id,
                        "level": 1,
                        "required": False,
                        "context_hint": "Auto-created by architect",
                        "content_md": "" if upd.status == "missing" else upd.content_md,
                        "is_manual": False,
                    }
                )
            else:
                data = {}
                if upd.status != "missing":
                    data["content_md"] = upd.content_md
                if data:
                    await self._db.llmdocumentsection.update(where={"id": existing.id}, data=data)

    async def mark_block_manual(self, project_id: int, block_id: str, content_md: str) -> None:
        existing = await self._db.llmdocumentsection.find_first(
            where={"project_id": project_id, "section_id": block_id}
        )
        if existing is None:
            await self._db.llmdocumentsection.create(
                data={
                    "project_id": project_id,
                    "section_id": block_id,
                    "title": block_id,
                    "level": 1,
                    "required": False,
                    "context_hint": "Manual section",
                    "content_md": content_md,
                    "is_manual": True,
                }
            )
            return

        await self._db.llmdocumentsection.update(
            where={"id": existing.id},
            data={"content_md": content_md, "is_manual": True},
        )

    async def build_document_snapshot(
        self,
        project_id: int,
        block_id: str,
        trigger_reason: str,
    ) -> DocumentSnapshot:
        await self._ensure_default_sections(project_id)
        await self._ensure_section(project_id, block_id)

        sections = await self._db.llmdocumentsection.find_many(where={"project_id": project_id})
        target = next((row for row in sections if row.section_id == block_id), None)
        if target is None:
            raise RuntimeError(f"Section {block_id} was not created")

        all_gkg = await self._db.llmgkgfact.find_many(where={"project_id": project_id})
        facts = [
            GKGFact(
                topic_id=row.id,
                scope=row.scope,
                property=row.property,
                value=row.value,
                status=row.status,
                source_ids=_as_source_ids(row.source_ids),
            )
            for row in all_gkg
        ]
        written_sections = [
            WrittenSection(
                section_id=row.section_id,
                title=row.title,
                content_md=row.content_md or "",
            )
            for row in sections
            if (row.content_md or "") and row.section_id != block_id
        ]

        return DocumentSnapshot(
            section_id=target.section_id,
            section_title=target.title,
            section_level=target.level,
            section_required=target.required,
            context_hint=target.context_hint,
            trigger_reason=trigger_reason,
            section_facts=facts,
            written_sections=written_sections,
        )

    async def consultant_search_gkg(self, project_id: int, query: str, limit: int) -> list[GKGSearchResult]:
        query_raw = getattr(self._db, "query_raw", None)
        if callable(query_raw):
            try:
                # Reuse existing embeddings from GKG row text to avoid adding a second embedder dependency layer.
                pseudo_embedding = [float(len(token)) for token in _tokenize(query)[:1024]]
                if pseudo_embedding:
                    vector = _to_pgvector_literal(pseudo_embedding + [0.0] * max(0, 1024 - len(pseudo_embedding)))
                    rows = await query_raw(
                        f"""
                        SELECT id, scope, property, value, status, rationale, source_ids,
                               (embedding_vector <=> '{vector}'::vector) AS distance
                        FROM \"LlmGkgFact\"
                        WHERE project_id = {int(project_id)}
                          AND embedding_vector IS NOT NULL
                        ORDER BY distance ASC
                        LIMIT {int(limit)}
                        """
                    )
                    if rows:
                        out: list[GKGSearchResult] = []
                        for row in rows:
                            score = 1.0 - float(row.get("distance", 1.0))
                            out.append(
                                GKGSearchResult(
                                    topic_id=str(row.get("id")),
                                    scope=str(row.get("scope")),
                                    property=str(row.get("property")),
                                    value=str(row.get("value")),
                                    status=str(row.get("status")),
                                    rationale=str(row.get("rationale") or ""),
                                    source_ids=_as_source_ids(row.get("source_ids")),
                                    score=round(max(score, 0.0), 4),
                                )
                            )
                        return out
            except Exception:
                # Fallback to lexical score below.
                pass

        rows = await self._db.llmgkgfact.find_many(where={"project_id": project_id})
        scored: list[tuple[float, object]] = []
        for row in rows:
            score = _score(query, f"{row.scope} {row.property} {row.value} {row.rationale} {row.content_raw}")
            if score <= 0:
                continue
            scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)

        return [
            GKGSearchResult(
                topic_id=row.id,
                scope=row.scope,
                property=row.property,
                value=row.value,
                status=row.status,
                rationale=row.rationale,
                source_ids=_as_source_ids(row.source_ids),
                score=round(score_value, 4),
            )
            for score_value, row in scored[:limit]
        ]

    async def consultant_get_gkg_node_detail(self, project_id: int, topic_id: str) -> GKGNodeDetail | None:
        row = await self._db.llmgkgfact.find_first(where={"project_id": project_id, "id": topic_id})
        if row is None:
            return None

        source_ids = list(row.source_ids or [])
        source_ids = _as_source_ids(row.source_ids)
        return GKGNodeDetail(
            topic_id=row.id,
            scope=row.scope,
            property=row.property,
            winning_value=row.value,
            rationale=row.rationale,
            evidence=[
                {
                    "quote": row.content_raw,
                    "author": "user",
                    "timestamp": "unknown",
                    "source_id": source_ids[0] if source_ids else "unknown",
                }
            ],
            rejected_alternatives=[],
        )

    async def consultant_search_raw_sources(
        self,
        project_id: int,
        query: str,
        limit: int,
    ) -> list[ConsultantSourceChunk]:
        rows = await self._db.llmrawsourcechunk.find_many(where={"project_id": project_id})
        scored: list[tuple[float, object]] = []
        for row in rows:
            score = _score(query, row.text)
            if score <= 0:
                continue
            scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)

        return [
            ConsultantSourceChunk(
                source_id=row.source_id,
                source_name=row.source_name,
                chunk_index=row.chunk_index,
                text=row.text,
                score=round(score_value, 4),
            )
            for score_value, row in scored[:limit]
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
                source_id=item.source_id,
                source_name=item.source_name,
                chunk_index=item.chunk_index,
                text=item.text,
                score=item.score,
            )
            for item in chunks
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

    async def create_resolved_node_from_pending_action(
        self,
        project_id: int,
        action_id: str,
        question: str,
        resolution: str,
    ) -> list[GKGNode]:
        node = GKGNode(
            scope="UserDecision",
            property=question[:120],
            value=resolution,
            content_raw=resolution,
            status="RESOLVED",
            source_ids=[f"pending_action:{action_id}"],
            rationale="User resolved pending action",
            embedding=[0.0, 0.0, 0.0],
        )
        await self.add_gkg_nodes(project_id, [node])
        return [node]
