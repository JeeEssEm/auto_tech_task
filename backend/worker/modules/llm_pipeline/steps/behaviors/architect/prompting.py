"""
prompting.py — промпты для ArchitectBehavior.

Архитектор работает посекционно: получает один блок шаблона за раз
и пишет для него content_md на основе GKG.

Цикл с инструментами нужен потому, что GKG содержит только краткие факты
(scope/property/value). Чтобы превратить «БД: ClickHouse» в связный абзац,
Архитектор должен углубиться в досье узла через get_context_details.
"""

from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import (
    GKGFact,
    ContextDetail,
    SourceChunk,
    ConsistencyCheckResult,
    WrittenSection
)


_TOOLS_SCHEMA = """
## Tools

### 1. get_context_details
Retrieve the full dossier for a GKG node: all evidence quotes, authors,
timestamps, and alternatives that were considered but rejected.

Use when: a fact from [SECTION FACTS] is too brief to write a full paragraph.
Example: fact says "DB: ClickHouse" — call this to get WHY it was chosen,
who proposed it, what was rejected.

Args:
  topic_id : string — exact topic_id from [SECTION FACTS]

Returns: winning value + rationale + evidence list + rejected alternatives.

### 2. search_raw_sources
Full-text / vector search over raw source chunks (documents, transcripts, chats).

Use when: [SECTION FACTS] has no relevant topics AND get_context_details
didn't help. This is the last resort before declaring data MISSING.

Args:
  query : string — search query (1–20 words, Russian or English)
  limit : integer — 1..3, default 2

Returns: raw text fragments with source name and chunk index.

### 3. ask_user
Create a pending question for the user when critical data is absent from both
GKG and raw sources. Suspends generation of this block.

Use when: a section is marked `required: true` in the template AND data is
completely absent after exhausting get_context_details + search_raw_sources.
Do NOT use for optional sections — mark them MISSING and move on.

Args:
  question : string — specific question in Russian
  options  : list[string] | null — suggested answer variants (if applicable)

Returns: action_id string. You MUST include it in pending_actions of your output.

### 4. validate_consistency
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

### Header level invariant (important!)
The block you are writing has a `level` field. Any header inside content_md
must be at least level+1. If block level=2, use ### or #### inside — never # or ##.
This prevents section "escaping" its parent when the document is assembled.

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
id: it_tech_stack | title: "Стек технологий" | level: 2 | required: true
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

    return f"""\
[CURRENT SECTION]
id       : {section_id}
title    : {section_title}
level    : {section_level}
required : {section_required}
hint     : {context_hint}

[TRIGGER]
{trigger_note}

[SECTION FACTS]
{facts_text}

[ALREADY WRITTEN SECTIONS]
{written_text}

Write the section now.
""".strip()
