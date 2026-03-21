from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.schemas import (
    SourceChunk,
    GKGNodeDetail, GKGSearchResult
)


def format_gkg_search_results(results: list[GKGSearchResult]) -> str:
    if not results:
        return "GKG: ничего не найдено по этому запросу."
    lines = []
    for r in results:
        lines.append(
            f"- topic_id: {r.topic_id!r} | scope: {r.scope} | property: {r.property}\n"
            f"  value: {r.value} | status: {r.status}\n"
            f"  rationale: {r.rationale}\n"
            f"  sources: {', '.join(r.source_ids)}"
        )
    return "\n".join(lines)


def format_gkg_node_detail(detail: GKGNodeDetail | None, topic_id: str) -> str:
    if detail is None:
        return f"GKG: узел {topic_id!r} не найден."

    evidence_lines = []
    for ev in detail.evidence:
        author = ev.get("author") or "—"
        ts = ev.get("timestamp") or ""
        quote = ev.get("quote", "")
        evidence_lines.append(f'  [{author}{" " + ts if ts else ""}] "{quote}"')

    rejected_lines = []
    for alt in detail.rejected_alternatives:
        rejected_lines.append(
            f"  - {alt.get('value', '?')}: {alt.get('rationale', '—')}"
        )

    evidence_block = evidence_lines if evidence_lines else ["  (нет цитат)"]

    parts = [
        f"topic_id: {detail.topic_id}",
        f"winning_value: {detail.winning_value}",
        f"rationale: {detail.rationale}",
        "evidence:",
        *evidence_block,
    ]
    if rejected_lines:
        parts += ["rejected_alternatives:", *rejected_lines]

    return "\n".join(parts)


def format_raw_source_results(chunks: list[SourceChunk]) -> str:
    if not chunks:
        return "Raw sources: ничего не найдено."
    lines = []
    for ch in chunks:
        lines.append(
            f"[{ch.source_name} / chunk {ch.chunk_index}] (score={ch.score:.2f})\n"
            f"{ch.text[:600]}{'...' if len(ch.text) > 600 else ''}"
        )
    return "\n\n".join(lines)
