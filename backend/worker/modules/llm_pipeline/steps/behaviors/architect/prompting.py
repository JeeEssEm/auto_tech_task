"""
prompting.py — промпты для ArchitectBehavior.

Архитектор работает посекционно: получает один блок шаблона за раз
и пишет для него content_md на основе GKG.

Цикл с инструментами нужен потому, что GKG содержит только краткие факты
(scope/property/value). Чтобы превратить «БД: ClickHouse» в связный абзац,
Архитектор должен углубиться в досье узла через get_context_details.
"""
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.campaign import ArchitectCampaign
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import (
    GKGFact,
    ContextDetail,
    SourceChunk,
    ConsistencyCheckResult,
    WrittenSection
)


_TOOLS_SCHEMA = """
## Tools

### 1. search_gkg
Semantic search over resolved facts in the Global Knowledge Graph.
Use this FIRST to find relevant facts for the current section.

Args:
  query : string  — search query in Russian or English (1–20 words)
  limit : integer — number of results, 1..20, default 10

Returns: list of matching facts (scope, property, value, topic_id).

### 2. get_context_details
Retrieve the full dossier for a GKG node: all evidence quotes, authors,
timestamps, and alternatives that were considered but rejected.

Use when: a fact from [SECTION FACTS] is too brief to write a full paragraph.
Example: fact says "DB: ClickHouse" — call this to get WHY it was chosen,
who proposed it, what was rejected.

Args:
  topic_id : string — exact topic_id from [SECTION FACTS]

Returns: winning value + rationale + evidence list + rejected alternatives.

### 3. search_raw_sources
Full-text / vector search over raw source chunks (documents, transcripts, chats).

Use when: [SECTION FACTS] has no relevant topics AND get_context_details
didn't help. This is the last resort before declaring data MISSING.

Args:
  query : string — search query (1–20 words, Russian or English)
  limit : integer — 1..3, default 2

Returns: raw text fragments with source name and chunk index.

### 4. ask_user
Create a pending question for the user when critical data is absent from both
GKG and raw sources. Suspends generation of this block.

Use when: a section is marked `required: true` in the template AND data is
completely absent after exhausting get_context_details + search_raw_sources.
Do NOT use for optional sections — mark them MISSING and move on.

Args:
  question : string — specific question in Russian
  options  : list[string] | null — suggested answer variants (if applicable)

Returns: action_id string. You MUST include it in pending_actions of your output.

### 5. validate_consistency
Check the draft you just wrote against already-completed sections of the document.
Catches contradictions like "React SPA in intro" vs "server-side rendering in tech stack".

Use when: you have finished writing content_md and want to verify it
before returning. Required if this section references technology or architecture
decisions that appeared in earlier sections.

Args:
  draft_text : string — the content_md you just wrote

Returns: {"status": "OK"} or {"status": "CONFLICT", "reason": "..."}
If CONFLICT — fix the contradiction in content_md before returning.
"""

_OUTPUT_FORMAT = """
## Output format

Return valid JSON only — no markdown fences, no text outside JSON.

### Option A — tool call:
{
  "is_final": false,
  "tool_name": "<get_context_details | search_raw_sources | ask_user | validate_consistency>",
  "tool_args": { ... },
  "reasoning": "<one sentence: why this call>"
}

### Option B — finished section:
{
  "is_final": true,
  "section_id": "<from [CURRENT SECTION]>",
  "content_md": "<markdown text, empty string if status=missing>",
  "status": "<generated | partial | missing>",
  "pending_actions": [
    {
      "action_id": "<from ask_user result>",
      "question": "<question text>",
      "options": ["...", "..."] | null
    }
  ]
}

Status rules:
- generated  → content_md is complete, all required data was found
- partial    → some optional sub-points are missing, but core content is written;
               missing parts are marked inline with [ДАННЫЕ ОТСУТСТВУЮТ: <what>]
- missing    → required data is completely absent; content_md is empty string;
               pending_actions contains the ask_user result
"""


_WRITING_RULES = """
## Writing rules

### Style
- Language: Russian, formal technical tone (as in GOST-style documentation).
- No marketing language. No filler phrases like "данная система позволяет...".
- Use Markdown: headers (###+ only — never # or ## inside content_md),
  bold for key terms, tables for comparisons, numbered lists for sequences.
- Be specific: write "PostgreSQL 16" not "реляционная СУБД".
- Density over length: one precise paragraph beats three vague ones.

### Headers inside content_md
Always use ## as the top-level header inside content_md.
Use ### for subsections within the section, #### for deeper nesting.
Never use # (h1) — it is reserved for the document title.

### Grounding (mandatory)
Every factual claim must end with a hidden reference tag:
  В качестве СУБД выбран ClickHouse `<ref id="topic_db_01" source="meeting_04.mp4" />`

Rules for refs:
- id    → topic_id from GKG fact or "raw:<source_id>:<chunk_index>" for raw source chunks
- source → human-readable source name (filename, "user_chat", "telegram_chat")
- Place the tag at the end of the sentence that contains the fact, not at end of paragraph.
- If a paragraph contains multiple facts, each sentence gets its own tag.
- Do NOT invent topic_ids. Only use ids you received from tool results or [SECTION FACTS].

### Anti-hallucination contract
If data for a point is not in GKG or raw sources:
- For optional points: write [ДАННЫЕ ОТСУТСТВУЮТ: <what is missing>] inline.
- For required points: call ask_user, return status=missing.
- NEVER invent "typical values", "industry standards", or "common practices"
  unless the user explicitly asked for it. A blank is better than a lie.
"""


_EXAMPLE = """
## Example reasoning cycle

[CURRENT SECTION]
id: it_tech_stack | title: "Стек технологий" | position: 3 | required: true
context_hint: "Языки, фреймворки, СУБД, очереди — все упомянутые технологии"

[SECTION FACTS]
- topic_id: "lang_01"   | scope: Backend  | property: Язык      | value: Python
- topic_id: "fw_01"     | scope: Backend  | property: Фреймворк | value: FastAPI
- topic_id: "db_01"     | scope: Database | property: Движок    | value: ClickHouse
- topic_id: "queue_01"  | scope: Queue    | property: Брокер    | value: (пусто — UNRESOLVED)

[ALREADY WRITTEN SECTIONS]
Раздел "Общее описание": "...REST API на базе Python-бэкенда, ориентированный на аналитику..."

--- Step 1: углубить db_01 ---
{
  "is_final": false,
  "tool_name": "get_context_details",
  "tool_args": {"topic_id": "db_01"},
  "reasoning": "Значение db_01 есть, но нужно обоснование для связного текста"
}

[TOOL RESULT]
winning_value: ClickHouse
rationale: Выбран для OLAP-нагрузки, Postgres отклонён как неоптимальный
evidence: [{"quote": "нам важна аналитика в реальном времени", "author": "Мария", "source": "call_03.mp4"}]
rejected: [{"value": "PostgreSQL", "rationale": "не оптимален для колоночных запросов"}]

--- Step 2: broker неизвестен — искать в raw sources ---
{
  "is_final": false,
  "tool_name": "search_raw_sources",
  "tool_args": {"query": "брокер очередь сообщений kafka rabbitmq", "limit": 2},
  "reasoning": "queue_01 UNRESOLVED — ищу в исходниках"
}

[TOOL RESULT]
Raw sources: ничего не найдено.

--- Step 3: пишем черновик, брокер идёт как MISSING ---
--- Step 4: validate_consistency ---
{
  "is_final": false,
  "tool_name": "validate_consistency",
  "tool_args": {
    "draft_text": "### Бэкенд\\n\\nЯзык разработки — **Python** `<ref id=\\"lang_01\\" source=\\"call_03.mp4\\" />`..."
  },
  "reasoning": "Проверяю черновик на противоречие с уже написанным введением"
}

[TOOL RESULT]
{"status": "OK"}

--- Step 5: финальный ответ ---
{
  "is_final": true,
  "section_id": "it_tech_stack",
  "content_md": "### Бэкенд\\n\\nЯзык разработки — **Python** `<ref id=\\"lang_01\\" source=\\"call_03.mp4\\" />`, фреймворк — **FastAPI** `<ref id=\\"fw_01\\" source=\\"call_03.mp4\\" />`.\\n\\n### База данных\\n\\nВ качестве СУБД выбран **ClickHouse** как оптимальное решение для OLAP-нагрузки и аналитики в реальном времени `<ref id=\\"db_01\\" source=\\"call_03.mp4\\" />`. PostgreSQL был рассмотрен и отклонён как неоптимальный для колоночных запросов.\\n\\n### Брокер сообщений\\n\\n[ДАННЫЕ ОТСУТСТВУЮТ: тип брокера очередей не определён]",
  "status": "partial",
  "pending_actions": []
}
"""


def format_section_facts(facts: list[GKGFact]) -> str:
    if not facts:
        return "(нет фактов — секция пустая в GKG)"
    lines = []
    for f in facts:
        status_marker = f" ⚠️ {f.status}" if f.status in ("UNRESOLVED",) else ""
        lines.append(
            f"- topic_id: {f.topic_id!r:30s} | scope: {f.scope:20s} "
            f"| property: {f.property:25s} | value: {f.value}{status_marker}"
        )
    return "\n".join(lines)


def format_written_sections(sections: list[WrittenSection]) -> str:
    if not sections:
        return "(это первая секция документа)"
    lines = []
    for s in sections:
        # Даём только резюме, не полный текст — чтобы не раздувать контекст
        preview = s.content_md[:300].replace("\n", " ")
        if len(s.content_md) > 300:
            preview += "..."
        lines.append(f'Раздел "{s.title}" (id: {s.section_id}): {preview}')
    return "\n\n".join(lines)


def format_tool_result_context_detail(detail: ContextDetail | None, topic_id: str) -> str:
    if detail is None:
        return f"GKG: узел {topic_id!r} не найден."

    evidence_lines = [
        f'  [{ev.get("author") or "—"}{" " + ev["timestamp"] if ev.get("timestamp") else ""}]'
        f' source={ev.get("source_id", "—")} | "{ev.get("quote", "")}"'
        for ev in detail.evidence
    ]
    rejected_lines = [
        f"  - {alt.get('value', '?')}: {alt.get('rationale', '—')}"
        for alt in detail.rejected_alternatives
    ]

    parts = [
        f"topic_id     : {detail.topic_id}",
        f"winning_value: {detail.winning_value}",
        f"rationale    : {detail.rationale}",
        "evidence:",
        *(evidence_lines or ["  (нет цитат)"]),
    ]
    if rejected_lines:
        parts += ["rejected_alternatives:", *rejected_lines]
    return "\n".join(parts)


def format_tool_result_raw_sources(chunks: list[SourceChunk]) -> str:
    if not chunks:
        return "Raw sources: ничего не найдено."
    lines = []
    for ch in chunks:
        lines.append(
            f"[{ch.source_name} / chunk {ch.chunk_index}] "
            f"source_id={ch.source_id} (score={ch.score:.2f})\n"
            f"{ch.text[:500]}{'...' if len(ch.text) > 500 else ''}"
        )
    return "\n\n".join(lines)


def format_tool_result_consistency(result: ConsistencyCheckResult) -> str:
    if result.status == "OK":
        return '{"status": "OK"}'
    return f'{{"status": "CONFLICT", "reason": "{result.reason}"}}'


def format_tool_result_ask_user(action_id: str) -> str:
    return f"ask_user succeeded. action_id: {action_id!r}"


def build_architect_system_prompt() -> str:
    """
    Системный промпт не содержит данных проекта — они идут в user prompt.
    Это позволяет кешировать system prompt на уровне провайдера (prefix caching).
    """
    return f"""\
You are The Architect — a technical writer agent for an auto-spec generation system.

## Your role
Write one section of a technical specification document (TЗ) at a time,
based strictly on the Global Knowledge Graph (GKG) provided to you.
You are the only agent that writes content. You NEVER modify the GKG.
You answer ONLY with tool calls or the final section JSON — nothing else.

{_TOOLS_SCHEMA}
{_OUTPUT_FORMAT}
{_WRITING_RULES}
{_EXAMPLE}
""".strip()


def build_architect_user_prompt(
    section_id: str,
    section_title: str,
    section_level: int,
    section_required: bool,
    context_hint: str,
    facts: list[GKGFact],
    written_sections: list[WrittenSection],
    trigger_reason: str,
    user_message: str = ""
) -> str:
    """
    trigger_reason: "explicit_regen_request" | "spec_block_affected" | "initial_generation"
    Влияет на то, насколько агрессивно Архитектор ищет данные.
    При explicit_regen_request — глубже копает raw sources.
    """
    facts_text = format_section_facts(facts)
    written_text = format_written_sections(written_sections)

    trigger_note = {
        "explicit_regen_request": (
            "⚡ User explicitly requested regeneration of this section. "
            "Use get_context_details and search_raw_sources more aggressively — "
            "look for details that may have been missed in the previous version."
        ),
        "spec_block_affected": (
            "🔄 GKG was updated and this section is now outdated. "
            "Focus on the changed facts. Do not rewrite parts that are still valid."
        ),
        "initial_generation": (
            "🆕 First-time generation. Cover all context_hint topics you find data for."
        ),
    }.get(trigger_reason, "")
    scope_warning = (
        "\n⚠️ IMPORTANT: Write content ONLY for this specific section. "
        "Do NOT include content that belongs to other sections. "
        f"Other sections ({', '.join(s.section_id for s in written_sections)}) "
        "already exist or will be written separately."
    )

    user_request_block = ""
    if user_message:
        user_request_block = f"\n[USER REQUEST]\n{user_message}\nFocus on what the user specifically asked.\n"

    return f"""\
[CURRENT SECTION]
id       : {section_id}
title    : {section_title}
level    : {section_level}
required : {section_required}
hint     : {context_hint}

[TRIGGER]
{trigger_note}
{user_request_block}
{scope_warning}

[SECTION FACTS]
{facts_text}

[ALREADY WRITTEN SECTIONS]
{written_text}

Write the section now.
""".strip()


def format_document_state(sections: list) -> str:  # list[SectionState]
    lines = []
    for sec in sections:
        status = "🔒 manual" if sec.is_manual else ("✅ written" if sec.content_md else "⬜ empty")
        preview = ""
        if sec.content_md and not sec.is_manual:
            preview = " | " + sec.content_md[:80].replace("\n", " ") + ("..." if len(sec.content_md) > 80 else "")
        lines.append(
            f"  {sec.level}. [{sec.section_id}] {sec.title} "
            f"({'required' if sec.required else 'optional'}) — {status}{preview}"
        )
    return "\n".join(lines)


def build_plan_system_prompt() -> str:
    return """\
You are The Architect — a technical writer agent for an auto-spec generation system.

## Phase 1: Planning

You will receive:
- The user's request (may be empty for automated triggers)
- The current state of the specification document (all sections with statuses)
- The trigger reason

Your task: decide WHICH sections to write and in WHAT ORDER.

## Rules
1. Never touch sections marked as 🔒 manual.
2. For trigger=initial_generation: include all empty required sections, 
   then all empty optional sections.
3. For trigger=spec_block_affected: include sections that are logically 
   affected by the GKG changes — look at context_hint and current content.
4. For trigger=explicit_regen_request: use user_message to understand 
   what sections to update. Can be one or many.
5. Write sections in the order they appear in the document (by position number).
6. If nothing needs writing — return empty sections_to_write.

## Output format
Return valid JSON only, no markdown:
{
  "sections_to_write": ["section_id_1", "section_id_2", ...],
  "reasoning": "<brief explanation of why these sections>"
}
""".strip()


def build_plan_user_prompt(
    campaign: ArchitectCampaign,
    section_facts: dict[str, list[GKGFact]] | None = None,
) -> str:
    trigger_descriptions = {
        "initial_generation": "🆕 Initial generation — fill the specification from scratch.",
        "spec_block_affected": "🔄 GKG was updated — some sections may be outdated.",
        "explicit_regen_request": "⚡ User explicitly requested changes.",
    }

    user_msg_block = f"\n[USER REQUEST]\n{campaign.user_message}\n" if campaign.user_message else ""

    lines = []
    for sec in sorted(campaign.document, key=lambda s: s.level):
        if sec.is_manual:
            status = "🔒 manual — skip"
            facts_note = ""
        else:
            status = "✅ written" if sec.content_md else "⬜ empty"
            if section_facts is not None:
                count = len(section_facts.get(sec.section_id, []))
                facts_note = f" | GKG facts available: {count}"
            else:
                facts_note = ""

        lines.append(
            f" {sec.level}. [{sec.section_id}] {sec.title} "
            f"({'required' if sec.required else 'optional'}) — {status}{facts_note}"
        )

    doc_state = "\n".join(lines)

    return f"""\
[TRIGGER]
{trigger_descriptions.get(campaign.trigger_reason, campaign.trigger_reason)}
{user_msg_block}
[DOCUMENT STATE]
{doc_state}

Decide which sections to write.
Only include sections that have GKG facts available (count > 0),
unless this is an explicit_regen_request from the user.
""".strip()
