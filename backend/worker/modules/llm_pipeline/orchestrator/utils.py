import re

import structlog

from backend.worker.modules.llm_pipeline.abstractions.ports import LLMChatPort

log = structlog.get_logger(__name__)


def _match_section_id_from_snapshot(doc_snapshot: str, quote: str) -> str | None:
    """
    Парсит строки вида '- [sec_id] Заголовок (len=N)' из doc_snapshot
    и возвращает section_id, заголовок которого лучше всего совпадает с quote.
    """
    pattern = r'\[([^\]]+)\]\s+([^\(]+)'
    matches = re.findall(pattern, doc_snapshot or "")
    if not matches:
        return None

    quote_lower = quote.lower()
    best_id, best_score = None, 0
    for section_id, title in matches:
        score = sum(1 for w in title.strip().lower().split() if w in quote_lower)
        if score > best_score:
            best_score, best_id = score, section_id

    return best_id or matches[0][0]


async def _pick_section_id_via_llm(
    chat_port: LLMChatPort,
    model: str,
    user_message: str,
    sections: list[tuple[str, str]],  # [(section_id, title), ...]
) -> str | None:
    if not sections:
        return None

    sections_text = "\n".join(f"  {sid}: {title}" for sid, title in sections)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a section picker for a technical specification document. "
                "Given a user request and a list of sections, return the section_id "
                "that best matches what the user wants to create or edit.\n"
                "Return ONLY valid JSON, no markdown:\n"
                '{"section_id": "<exact id from the list>"}\n'
                "If nothing matches, return: {\"section_id\": null}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Available sections:\n{sections_text}\n\n"
                f"User request: {user_message}"
            ),
        },
    ]

    from pydantic import BaseModel

    class _Pick(BaseModel):
        section_id: str | None

    try:
        result = await chat_port.chat(
            messages=messages,
            model=model,
            temperature=0.0,
            max_tokens=64,
            response_model=_Pick,
        )
        return result.section_id
    except Exception as e:
        log.warning("pick_section_id | LLM failed: %s", e)
        return None
