from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.staging import StagingNode
from backend.worker.modules.llm_pipeline.steps.embedder.schemas import EmbeddedStagingNode

JUDGE_SYSTEM_PROMPT = """\
Ты — аналитик технической документации. Тебе дан кластер фактов, \
извлечённых из разных источников (документы, чаты, переговоры). \
Все факты относятся к одной теме (scope + property), но содержат разные значения.

Твоя задача — принять одно из трёх решений:

1. RESOLVED — ты можешь выбрать один факт как финальный.
   Критерии выбора (в порядке приоритета):
   a) Явная отмена: в тексте одного источника прямо сказано, что предыдущее решение меняется
      (например, "забудьте про X, теперь Y", "передумали, берём Z").
   b) Хронология: если timestamp доступен — более поздняя запись побеждает.
   c) Явный консенсус: несколько участников согласились с одним вариантом.

2. UNRESOLVED — ты НЕ можешь выбрать победителя.
   Когда использовать: равнозначные источники без временного сигнала, \
   взаимоисключающие варианты без явного финала.
   Не угадывай. Лучше UNRESOLVED, чем неверный RESOLVED.

3. SPLIT — факты в кластере оказались про разные вещи.
   Когда использовать: scope или property у нод фактически разные, \
   хотя формально совпали при группировке.
   Пример: "движок БД: Postgres" и "схема хранения: event sourcing" — \
   это две независимые темы, не конфликт.
   При SPLIT каждая группа становится отдельным фактом со статусом NO_CONFLICT.

Отвечай ТОЛЬКО валидным JSON без markdown-обёртки. Схема ответа:
{
  "verdict": "RESOLVED" | "UNRESOLVED" | "SPLIT",
  "winning_index": <int, только для RESOLVED — индекс ноды в списке ниже>,
  "split_groups": <[[int, ...], ...], только для SPLIT — группы индексов>,
  "rationale": "<string — обязательно, объясни решение>"
}
"""


def _format_node_for_judge(index: int, node: StagingNode) -> str:
    lines = [
        f"[{index}]",
        f"  source_id : {node.source_id}",
        f"  value     : {node.value}",
        f"  timestamp : {node.timestamp or '—'}",
        f"  author    : {node.author or '—'}",
        f"  quote     : {node.content_raw[:300]}{'...' if len(node.content_raw) > 300 else ''}",
    ]
    return "\n".join(lines)


def build_judge_prompt(cluster: list[EmbeddedStagingNode]) -> str:
    first = cluster[0].node
    header = (
        f"Тема: scope='{first.scope}', property='{first.property}'\n"
        f"Количество фактов: {len(cluster)}\n\n"
        "Факты:\n"
    )
    nodes_text = "\n\n".join(
        _format_node_for_judge(i, enode.node)
            for i, enode in enumerate(cluster)
    )
    return header + nodes_text
