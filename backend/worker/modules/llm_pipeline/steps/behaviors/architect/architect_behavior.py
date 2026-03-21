from typing import Any

from pydantic import TypeAdapter

from backend.worker.modules.llm_pipeline.abstractions.ports import LLMChatPort
from backend.worker.modules.llm_pipeline.providers.utils.json_utils import (
    escape_control_chars_in_strings,
    extract_first_json_object
)
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.context import ArchitectContext
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.abstractions.schemas import DocumentSnapshot
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.config import ArchitectSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.prompting import (
    build_architect_system_prompt,
    build_architect_user_prompt, format_tool_result_context_detail, format_tool_result_raw_sources,
    format_tool_result_ask_user, format_tool_result_consistency
)
from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import (
    SectionOutput, ArchitectResponse,
    PendingAction, ArchitectLLMOutput
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
                # Объединяем pending_actions от ask_user с теми что в SectionOutput
                # (LLM сам вставляет их в ответ, но мы дублируем для надёжности)
                all_actions = _merge_pending_actions(
                    pending_actions, output.pending_actions
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
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[SYSTEM] Duplicate tool call. "
                            "The result is already in the conversation above. "
                            "Use it and proceed."
                        ),
                    }
                )
                tool_calls_made += 1
                continue

            seen_calls.add(dedup_key)

            tool_result, side_effect = await self._dispatch_tool(
                tool_name=output.tool_name,
                tool_args=output.tool_args,
                written_sections=snapshot.written_sections,
                pending_actions=pending_actions,
                consistency_retries=consistency_retries,
            )

            # validate_consistency вернул CONFLICT — особый случай:
            # не просто добавляем результат, а добавляем инструкцию исправить
            if side_effect == "consistency_conflict":
                if consistency_retries < self._settings.max_consistency_retries:
                    consistency_retries += 1
                    messages.append({"role": "assistant", "content": output.model_dump_json()})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"[TOOL RESULT]\n{tool_result}\n\n"
                                "[SYSTEM] There is a contradiction. "
                                "Fix it in your content_md and return the corrected final answer. "
                                "Do NOT call validate_consistency again."
                            ),
                        }
                    )
                else:
                    # Лимит retry исчерпан — пишем как есть с пометкой
                    messages.append({"role": "assistant", "content": output.model_dump_json()})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"[TOOL RESULT]\n{tool_result}\n\n"
                                "[SYSTEM] Consistency fix attempts exhausted. "
                                "Return the section as-is. "
                                "Add a comment [ТРЕБУЕТ ПРОВЕРКИ: <conflict>] "
                                "at the end of content_md."
                            ),
                        }
                    )
            else:
                messages.append({"role": "assistant", "content": output.model_dump_json()})
                messages.append(
                    {
                        "role": "user",
                        "content": f"[TOOL RESULT]\n{tool_result}",
                    }
                )

            tool_calls_made += 1

        messages.append({"role": "user", "content": _TRUNCATION_MESSAGE})
        final_output = await self._call_llm(messages)

        if isinstance(final_output, SectionOutput):
            all_actions = _merge_pending_actions(pending_actions, final_output.pending_actions)
            return ArchitectResponse(
                section_id=final_output.section_id,
                content_md=final_output.content_md,
                status=final_output.status,
                pending_actions=all_actions,
                used_tool_calls=tool_calls_made,
                was_truncated=True,
            )

        return ArchitectResponse(
            section_id=snapshot.section_id,
            content_md="",
            status="missing",
            pending_actions=pending_actions,
            used_tool_calls=tool_calls_made,
            was_truncated=True,
        )

    async def _call_llm(self, messages: list[dict]) -> ArchitectLLMOutput:
        raw = await self._chat.chat(
            messages=messages,
            model=self._settings.model,
            temperature=self._settings.temperature,
            max_tokens=self._settings.max_tokens,
            response_model=str,
        )
        cleaned = escape_control_chars_in_strings(
            extract_first_json_object(raw)
        )
        return _output_adapter.validate_json(cleaned)

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
