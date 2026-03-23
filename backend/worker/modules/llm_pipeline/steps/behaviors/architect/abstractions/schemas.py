from dataclasses import dataclass, field

from backend.worker.modules.llm_pipeline.steps.behaviors.architect.schemas import GKGFact, WrittenSection


@dataclass
class DocumentSnapshot:
    """
    Всё что нужно Архитектору перед запуском.
    Заполняется на уровне API-обработчика.

    Разделение на section_facts и written_sections позволяет:
    - section_facts: загружать только факты, семантически близкие к context_hint
      (SQL-запрос с векторным поиском, а не весь GKG)
    - written_sections: передавать только уже готовые секции для cross-check,
      без черновиков и пустых блоков
    """
    section_id: str
    section_title: str
    section_level: int              # 1 | 2 | 3
    section_required: bool
    context_hint: str
    trigger_reason: str             # explicit_regen_request | spec_block_affected | initial_generation

    # Факты из GKG, релевантные этой секции (отбор по embedding <=> hint_vector)
    section_facts: list[GKGFact] = field(default_factory=list)

    # Уже написанные секции документа (для validate_consistency)
    written_sections: list[WrittenSection] = field(default_factory=list)
    user_message: str = ""
