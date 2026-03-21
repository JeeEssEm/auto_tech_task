from dataclasses import dataclass


@dataclass
class ProjectSnapshot:
    """
    Минимальный набор данных для построения project_context.
    Заполняется на уровне API-обработчика перед вызовом ConsultantBehavior.run().
    """
    project_name: str
    project_type: str  # "IT-проект", "Строительный" и т.д.
    total_gkg_nodes: int
    unresolved_conflicts: int
    doc_section_titles: list[str]  # плоский список заголовков ТЗ (уровни 1-2)
    # Топ-10 scope'ов по числу нод — чтобы LLM понимал «карту» знаний
    top_scopes: list[str]


class ProjectContextBuilder:
    """
    Собирает project_context — компактный текст для system prompt.

    Намеренно не обращается к LLM и не делает SQL-запросов — только форматирует
    уже собранный ProjectSnapshot. Это упрощает тестирование и убирает
    дополнительные сетевые вызовы перед запуском агентного цикла.

    Использование:
        snapshot = ProjectSnapshot(...)
        context = ProjectContextBuilder.build(snapshot)
        # → передаётся в build_consultant_system_prompt(project_context=context)
    """

    # Сколько заголовков разделов показывать в снепшоте.
    # Остальные обрезаются — LLM и так их найдёт через инструменты.
    _MAX_SECTIONS = 12
    _MAX_SCOPES = 8

    @classmethod
    def build(cls, snapshot: ProjectSnapshot) -> str:
        sections = snapshot.doc_section_titles[:cls._MAX_SECTIONS]
        sections_text = "\n".join(f"  - {t}" for t in sections)
        if len(snapshot.doc_section_titles) > cls._MAX_SECTIONS:
            omitted = len(snapshot.doc_section_titles) - cls._MAX_SECTIONS
            sections_text += f"\n  ... и ещё {omitted} разделов"

        scopes = snapshot.top_scopes[:cls._MAX_SCOPES]
        scopes_text = ", ".join(scopes) if scopes else "—"

        conflicts_note = (
            f"⚠️ Неразрешённых конфликтов в GKG: {snapshot.unresolved_conflicts}"
            if snapshot.unresolved_conflicts > 0
            else "Конфликтов в GKG нет"
        )

        return (
            f"Project: «{snapshot.project_name}» ({snapshot.project_type})\n"
            f"GKG facts: {snapshot.total_gkg_nodes} | {conflicts_note}\n"
            f"Main knowledge areas: {scopes_text}\n"
            f"Spec sections:\n{sections_text}"
        )
