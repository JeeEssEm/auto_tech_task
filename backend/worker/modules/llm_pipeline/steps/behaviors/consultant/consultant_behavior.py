import json
from typing import Any

from pydantic import TypeAdapter

from backend.worker.modules.llm_pipeline.abstractions.ports import LLMChatPort
from backend.worker.modules.llm_pipeline.providers.utils.json_utils import (
    extract_first_json_object,
    escape_control_chars_in_strings
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.abstractions.context import ConsultantContext
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.config import ConsultantSettings
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.context import (
    ProjectSnapshot,
    ProjectContextBuilder
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.formatting import (
    format_gkg_search_results,
    format_gkg_node_detail,
    format_raw_source_results,
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.prompting import (
    build_consultant_system_prompt,
    build_consultant_user_prompt
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.schemas import (
    ConsultantResponse,
    ConsultantLLMOutput, FinalAnswerOutput
)
from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.utils import _clamp, _require_str, _make_dedup_key

_output_adapter: TypeAdapter[ConsultantLLMOutput] = TypeAdapter(ConsultantLLMOutput)

_TRUNCATION_MESSAGE = (
    "[SYSTEM] You have reached the tool call limit. "
    "Give your final answer NOW based on what you already found. "
    "If information is incomplete — say so explicitly. "
    'Return {"is_final": true, ...} schema only.'
)


class ConsultantBehavior:
    def __init__(
            self,
            chat_port: LLMChatPort,
            context: ConsultantContext,
            settings: ConsultantSettings,
    ) -> None:
        self._chat = chat_port
        self._context = context
        self._settings = settings

    async def run(
            self,
            question: str,
            snapshot: ProjectSnapshot
    ) -> ConsultantResponse:
        project_context = ProjectContextBuilder.build(snapshot)

        messages = [
            {"role": "system", "content": build_consultant_system_prompt(project_context)},
            {"role": "user", "content": build_consultant_user_prompt(question)},
        ]
        seen_calls: set[str] = set()
        tool_calls_made = 0

        while tool_calls_made < self._settings.max_tool_calls:
            output = await self._call_llm(messages)

            if isinstance(output, FinalAnswerOutput):
                return ConsultantResponse(
                    answer=output.answer,
                    used_tool_calls=tool_calls_made,
                    source_refs=output.source_refs,
                    was_truncated=False,
                )

            dedup_key = _make_dedup_key(output)
            if dedup_key in seen_calls:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[SYSTEM] You already called this exact tool with the same arguments. "
                            "The result is already above. Do not repeat — use what you have."
                        ),
                    }
                )
                tool_calls_made += 1
                continue

            seen_calls.add(dedup_key)

            tool_result_text = await self._dispatch_tool(
                tool_name=output.tool_name,
                tool_args=output.tool_args,
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": output.model_dump_json(),
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": f"[TOOL RESULT]\n{tool_result_text}",
                }
            )
            tool_calls_made += 1

        messages.append(
            {
                "role": "user",
                "content": _TRUNCATION_MESSAGE,
            }
        )
        final = await self._call_llm(messages)
        if isinstance(final, FinalAnswerOutput):
            return ConsultantResponse(
                answer=final.answer,
                used_tool_calls=tool_calls_made,
                source_refs=final.source_refs,
                was_truncated=True,
            )

        return ConsultantResponse(
            answer=(
                "Не хватает данных, чтобы дать точный ответ в текущем лимите обращений к источникам. "
                "Сформулируйте вопрос уже или увеличьте лимит tool calls."
            ),
            used_tool_calls=tool_calls_made,
            source_refs=[],
            was_truncated=True,
        )

    async def _dispatch_tool(
            self,
            tool_name: str,
            tool_args: dict[str, Any],
    ) -> str:
        """
        Маршрутизирует вызов к ConsultantContext и форматирует результат в текст.

        Параметры limit намеренно зажаты через _clamp:
        LLM не должен управлять объёмом возвращаемых данных сверх разумного.
        """
        match tool_name:
            case "search_gkg":
                query = _require_str(tool_args, "query")
                limit = _clamp(tool_args.get("limit", 3), lo=1, hi=5)
                results = await self._context.search_gkg(query=query, limit=limit)
                return format_gkg_search_results(results)

            case "get_gkg_node_detail":
                topic_id = _require_str(tool_args, "topic_id")
                detail = await self._context.get_gkg_node_detail(topic_id=topic_id)
                return format_gkg_node_detail(detail, topic_id)

            case "search_raw_sources":
                query = _require_str(tool_args, "query")
                limit = _clamp(tool_args.get("limit", 2), lo=1, hi=3)
                chunks = await self._context.search_raw_sources(query=query, limit=limit)
                return format_raw_source_results(chunks)

            case _:
                return (
                    f"[ERROR] Unknown tool: {tool_name!r}. "
                    "Available: search_gkg, get_gkg_node_detail, search_raw_sources."
                )

    async def _call_llm(self, messages: list[dict]) -> ConsultantLLMOutput:
        raw = await self._chat.chat(
            messages=messages,
            model=self._settings.model,
            temperature=self._settings.temperature,
            max_tokens=self._settings.max_tokens,
            response_model=str
        )
        raw = extract_first_json_object(raw)
        raw = escape_control_chars_in_strings(raw)

        return _output_adapter.validate_json(raw)
