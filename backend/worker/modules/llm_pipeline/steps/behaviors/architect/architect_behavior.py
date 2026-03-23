import asyncio
from typing import Any

import structlog
from pydantic import TypeAdapter

from backend.worker.modules.llm_pipeline.abstractions.ports import LLMChatPort
from backend.worker.modules.llm_pipeline.providers.utils.json_utils import (
    escape_control_chars_in_strings,
    extract_first_json_object
)
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.context import ArchitectContext
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.schemas import DocumentSnapshot
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.campaign import (
    ArchitectCampaign, SectionState,
    SectionPlan
)
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.config import ArchitectSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.prompting import (
    build_architect_system_prompt,
    build_architect_user_prompt, format_tool_result_context_detail, format_tool_result_raw_sources,
    format_tool_result_ask_user, format_tool_result_consistency, build_plan_system_prompt, build_plan_user_prompt
)
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import (
    SectionOutput, ArchitectResponse,
    PendingAction, ArchitectLLMOutput, WrittenSection, GKGFact
)
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.utils import _merge_pending_actions
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.utils import _make_dedup_key, _require_str, _clamp

_TRUNCATION_MESSAGE = (
    "[SYSTEM] You have reached the tool call limit. "
    "Write the best section you can from what you already have. "
    "Mark missing data inline with [ДАННЫЕ ОТСУТСТВУЮТ: <what>]. "
    'Return {"is_final": true, ...} schema only.'
)

_output_adapter: TypeAdapter[ArchitectLLMOutput] = TypeAdapter(ArchitectLLMOutput)
_plan_adapter: TypeAdapter[SectionPlan] = TypeAdapter(SectionPlan)
log = structlog.get_logger(__name__)


class ArchitectBehavior:
    def __init__(
            self,
            chat_port: LLMChatPort,
            context: ArchitectContext,
            settings: ArchitectSettings,
    ) -> None:
        self._chat = chat_port
        self._context = context
        self._settings = settings

    async def run(self, snapshot: DocumentSnapshot) -> ArchitectResponse:
        log.info(
            "architect_run_started",
            section_id=snapshot.section_id,
            section_title=snapshot.section_title,
            trigger_reason=snapshot.trigger_reason,
            facts_count=len(snapshot.section_facts),
            written_sections_count=len(snapshot.written_sections),
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": build_architect_system_prompt()},
            {
                "role": "user",
                "content": build_architect_user_prompt(
                    section_id=snapshot.section_id,
                    section_title=snapshot.section_title,
                    section_level=snapshot.section_level,
                    section_required=snapshot.section_required,
                    context_hint=snapshot.context_hint,
                    facts=snapshot.section_facts,
                    written_sections=snapshot.written_sections,
                    trigger_reason=snapshot.trigger_reason,
                    user_message=snapshot.user_message,
                ),
            },
        ]

        seen_calls: set[str] = set()
        tool_calls_made = 0
        pending_actions: list[PendingAction] = []
        consistency_retries = 0

        while tool_calls_made < self._settings.max_tool_calls:
            output = await self._call_llm(messages)

            if isinstance(output, SectionOutput):
                all_actions = _merge_pending_actions(pending_actions, output.pending_actions)
                log.info(
                    "architect_run_finished",
                    section_id=output.section_id,
                    status=output.status,
                    used_tool_calls=tool_calls_made,
                    pending_actions=len(all_actions),
                    was_truncated=False,
                )
                return ArchitectResponse(
                    section_id=output.section_id,
                    content_md=output.content_md,
                    status=output.status,
                    pending_actions=all_actions,
                    used_tool_calls=tool_calls_made,
                    was_truncated=False,
                )

            dedup_key = _make_dedup_key(output)
            if dedup_key in seen_calls:
                log.warning(
                    "architect_duplicate_tool_call",
                    section_id=snapshot.section_id,
                    tool_name=output.tool_name,
                    tool_args=output.tool_args,
                    dedup_key=dedup_key,
                )
                messages.append({"role": "user", "content": "[SYSTEM] Duplicate tool call. Use result already in context."})
                tool_calls_made += 1
                continue
            seen_calls.add(dedup_key)

            log.info(
                "architect_tool_call",
                section_id=snapshot.section_id,
                tool_name=output.tool_name,
                tool_args=output.tool_args,
                tool_calls_made=tool_calls_made,
            )

            tool_result, side_effect = await self._dispatch_tool(
                tool_name=output.tool_name,
                tool_args=output.tool_args,
                written_sections=snapshot.written_sections,
                pending_actions=pending_actions,
                consistency_retries=consistency_retries,
            )

            log.info(
                "architect_tool_result",
                section_id=snapshot.section_id,
                tool_name=output.tool_name,
                side_effect=side_effect,
                result_preview=tool_result,
            )

            if side_effect == "consistency_conflict":
                if consistency_retries < self._settings.max_consistency_retries:
                    consistency_retries += 1
                    messages.append({"role": "assistant", "content": output.model_dump_json()})
                    messages.append({"role": "user", "content": f"[TOOL RESULT]\n{tool_result}\n\n[SYSTEM] Fix contradiction and return corrected final answer."})
                else:
                    messages.append({"role": "assistant", "content": output.model_dump_json()})
                    messages.append({"role": "user", "content": f"[TOOL RESULT]\n{tool_result}\n\n[SYSTEM] Consistency fix exhausted. Add [ТРЕБУЕТ ПРОВЕРКИ: <conflict>] at end of content_md."})
            else:
                messages.append({"role": "assistant", "content": output.model_dump_json()})
                messages.append({"role": "user", "content": f"[TOOL RESULT]\n{tool_result}"})

            tool_calls_made += 1

        messages.append({"role": "user", "content": _TRUNCATION_MESSAGE})
        final_output = await self._call_llm(messages)

        if isinstance(final_output, SectionOutput):
            all_actions = _merge_pending_actions(pending_actions, final_output.pending_actions)
            log.warning(
                "architect_run_finished_with_truncation",
                section_id=final_output.section_id,
                status=final_output.status,
                used_tool_calls=tool_calls_made,
                pending_actions=len(all_actions),
                was_truncated=True,
            )
            return ArchitectResponse(
                section_id=final_output.section_id,
                content_md=final_output.content_md,
                status=final_output.status,
                pending_actions=all_actions,
                used_tool_calls=tool_calls_made,
                was_truncated=True,
            )

        log.warning(
            "architect_run_failed_to_finalize",
            section_id=snapshot.section_id,
            used_tool_calls=tool_calls_made,
            pending_actions=len(pending_actions),
        )
        return ArchitectResponse(
            section_id=snapshot.section_id,
            content_md="",
            status="missing",
            pending_actions=pending_actions,
            used_tool_calls=tool_calls_made,
            was_truncated=True,
        )

    async def run_campaign(self, campaign: ArchitectCampaign) -> list[ArchitectResponse]:
        log.info(
            "architect_campaign_started",
            trigger_reason=campaign.trigger_reason,
            sections_total=len(campaign.document),
            forced_sections=campaign.forced_sections,
        )
        section_map = {s.section_id: s for s in campaign.document}

        if campaign.forced_sections:
            to_write = [
                sid for sid in campaign.forced_sections
                if sid in {s.section_id for s in campaign.document}
                   and not next(s for s in campaign.document if s.section_id == sid).is_manual
            ]
        else:
            section_facts = await self._prefetch_all_sections(campaign.document)

            plan = await self._plan(campaign, section_facts)
            if not plan.sections_to_write:
                return []

            to_write = [
                sid for sid in plan.sections_to_write
                if sid in section_map and not section_map[sid].is_manual
            ]

            if not to_write:
                return []

        # Фаза 3: пишем секции последовательно
        # Последовательно (не параллельно) — каждая следующая секция
        # видит уже написанные предыдущие через written_sections
        written: list[ArchitectResponse] = []
        written_sections: list[WrittenSection] = [
            WrittenSection(
                section_id=s.section_id,
                title=s.title,
                content_md=s.content_md,
            )
            for s in campaign.document
            if s.content_md and not s.is_manual
        ]

        for section_id in to_write:
            sec = section_map[section_id]
            log.info(
                "architect_campaign_section_started",
                section_id=section_id,
                title=sec.title,
                trigger_reason=campaign.trigger_reason,
            )
            snapshot = DocumentSnapshot(
                section_id=sec.section_id,
                section_title=sec.title,
                section_level=sec.level,
                section_required=sec.required,
                context_hint=sec.context_hint,
                trigger_reason=campaign.trigger_reason,
                section_facts=await self._fetch_facts_for_section(sec),
                written_sections=written_sections,
                user_message=campaign.user_message,
            )
            response = await self.run(snapshot)
            response.section_id = sec.section_id
            log.info(
                "architect_campaign_section_finished",
                section_id=section_id,
                status=response.status,
                pending_actions=len(response.pending_actions),
                was_truncated=response.was_truncated,
            )

            written.append(response)

            if response.content_md:
                written_sections.append(WrittenSection(
                    section_id=sec.section_id,
                    title=sec.title,
                    content_md=response.content_md,
                ))

        return written

    async def _prefetch_all_sections(
            self,
            document: list[SectionState],
    ) -> dict[str, list[GKGFact]]:
        """
        Параллельно загружаем факты для всех секций.
        Результат передаём в план — LLM видит у каких секций есть данные.
        """

        async def fetch_one(sec: SectionState) -> tuple[str, list[GKGFact]]:
            facts = await self._fetch_facts_for_section(sec)
            return sec.section_id, facts

        results = await asyncio.gather(*[fetch_one(s) for s in document if not s.is_manual])
        cache = dict(results)
        self._facts_cache = cache
        return cache

    async def _fetch_facts_for_section(self, sec: SectionState) -> list[GKGFact]:
        """
        Тянет релевантные факты из GKG через search_gkg.
        Используем context_hint + title как поисковый запрос.
        """
        query = f"{sec.title}. {sec.context_hint}"
        try:
            results = await self._context.search_gkg(query=query, limit=15)
        except Exception:
            return []

        return [
            GKGFact(
                topic_id=r.topic_id,
                scope=r.scope,
                property=r.property,
                value=r.value,
                status=r.status,
                source_ids=r.source_ids,
            )
            for r in results
        ]

    async def _plan(
            self,
            campaign: ArchitectCampaign,
            section_facts: dict[str, list[GKGFact]] | None = None,
    ) -> SectionPlan:
        messages = [
            {"role": "system", "content": build_plan_system_prompt()},
            {"role": "user", "content": build_plan_user_prompt(campaign, section_facts)}
        ]
        raw = await self._chat.chat(
            messages=messages,
            model=self._settings.model,
            temperature=0.0,
            max_tokens=512,
            response_model=str,
        )
        try:
            cleaned = escape_control_chars_in_strings(extract_first_json_object(raw))
            return _plan_adapter.validate_json(cleaned)
        except Exception:
            # Fallback: только секции у которых реально есть факты
            if section_facts:
                return SectionPlan(
                    sections_to_write=[
                        sid for sid, facts in section_facts.items()
                        if facts and not next(
                            (s for s in campaign.document if s.section_id == sid and s.is_manual), None
                        )
                    ],
                    reasoning="fallback: only sections with available GKG facts",
                )
            return SectionPlan(
                sections_to_write=[
                    s.section_id for s in campaign.document
                    if not s.content_md and not s.is_manual and s.required
                ],
                reasoning="fallback: plan parsing failed, no facts cache",
            )

    async def _call_llm(self, messages: list[dict]) -> ArchitectLLMOutput:
        log.info(
            "architect_llm_call",
            messages_count=len(messages),
            max_tokens=self._settings.max_tokens,
            temperature=self._settings.temperature,
        )
        raw = await self._chat.chat(
            messages=messages,
            model=self._settings.model,
            temperature=self._settings.temperature,
            max_tokens=self._settings.max_tokens,
            response_model=str,
        )
        try:
            cleaned = escape_control_chars_in_strings(
                extract_first_json_object(raw)
            )
            return _output_adapter.validate_json(cleaned)
        except Exception:
            log.exception("architect_llm_parse_failed", raw_response=raw)
            raise

    async def _dispatch_tool(
            self,
            tool_name: str,
            tool_args: dict[str, Any],
            written_sections: list,
            pending_actions: list[PendingAction],
            consistency_retries: int,
    ) -> tuple[str, str | None]:
        """
        Возвращает (tool_result_text, side_effect | None).

        side_effect:
          "consistency_conflict" — validate_consistency вернул CONFLICT,
                                   нужна специальная обработка в цикле.
          None                  — обычный инструмент, просто добавить в историю.
        """
        match tool_name:
            case "search_gkg":
                query = _require_str(tool_args, "query")
                limit = _clamp(tool_args.get("limit", 10), lo=1, hi=20)
                results = await self._context.search_gkg(query=query, limit=limit)

                from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.formatting import format_gkg_search_results

                return format_gkg_search_results(results), None

            case "get_context_details":
                topic_id = _require_str(tool_args, "topic_id")
                detail = await self._context.get_context_details(topic_id=topic_id)
                return format_tool_result_context_detail(detail, topic_id), None

            case "search_raw_sources":
                query = _require_str(tool_args, "query")
                limit = _clamp(tool_args.get("limit", 2), lo=1, hi=3)
                chunks = await self._context.search_raw_sources(query=query, limit=limit)
                return format_tool_result_raw_sources(chunks), None

            case "ask_user":
                question = _require_str(tool_args, "question")
                options = tool_args.get("options")
                if isinstance(options, list):
                    options = [str(o) for o in options]
                else:
                    options = None
                action_id = await self._context.ask_user(
                    question=question, options=options
                )
                # Накапливаем side-effect локально — LLM тоже добавит в pending_actions,
                # но мы дублируем на случай если он забудет
                pending_actions.append(
                    PendingAction(action_id=action_id, question=question, options=options)
                )
                return format_tool_result_ask_user(action_id), None

            case "validate_consistency":
                draft_text = _require_str(tool_args, "draft_text")
                result = await self._context.validate_consistency(
                    draft_text=draft_text,
                    written_sections=written_sections,
                )
                formatted = format_tool_result_consistency(result)
                side_effect = "consistency_conflict" if result.status == "CONFLICT" else None
                return formatted, side_effect

            case _:
                return (
                    f"[ERROR] Unknown tool: {tool_name!r}. "
                    "Available: get_context_details, search_raw_sources, ask_user, validate_consistency."
                ), None
