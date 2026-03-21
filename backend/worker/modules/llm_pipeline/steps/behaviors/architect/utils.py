from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import PendingAction


def _merge_pending_actions(
    accumulated: list[PendingAction],
    from_llm: list[PendingAction],
) -> list[PendingAction]:
    """
    Объединяет pending_actions из двух источников без дублей по action_id.
    Источник истины — accumulated (мы сами вызвали ask_user и получили action_id).
    from_llm может содержать те же action_id (LLM повторяет их в SectionOutput) —
    они дедуплицируются.
    """
    seen_ids = {a.action_id for a in accumulated}
    extras = [a for a in from_llm if a.action_id not in seen_ids]
    return accumulated + extras
