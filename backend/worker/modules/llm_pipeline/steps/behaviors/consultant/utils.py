import json
from typing import Any

from backend.worker.modules.llm_pipeline.steps.behaviors.consultant.schemas import ToolCallOutput


def _clamp(value: Any, lo: int, hi: int) -> int:
    """Приводит значение к целому и зажимает в диапазон [lo, hi]."""
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return lo


def _require_str(args: dict, key: str) -> str:
    """Извлекает строковый аргумент или бросает ValueError."""
    val = args.get(key, "")
    if not isinstance(val, str) or not val.strip():
        raise ValueError(
            f"Tool argument {key!r} must be a non-empty string, got {val!r}"
        )
    return val.strip()


def _make_dedup_key(output: ToolCallOutput) -> str:
    """Детерминированный ключ для дедупликации вызовов инструментов."""
    return f"{output.tool_name}:{json.dumps(output.tool_args, sort_keys=True, ensure_ascii=False)}"
