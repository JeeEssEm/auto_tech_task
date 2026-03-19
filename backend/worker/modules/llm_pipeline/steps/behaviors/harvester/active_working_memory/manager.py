# awm.py

from typing import Callable

from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.active_working_memory.schemas import (
    AWMState,
    AWMTopic, AWMStatus, Evidence
)
from backend.worker.modules.llm_pipeline.steps.behaviors.harvester.llm_response_commands import (
    HarvesterLLMOutput,
    ResolveCommand
)

EVICTION_STALENESS_THRESHOLD = 12   # чанков


class AWMManager:
    def __init__(
        self,
        state: AWMState | None = None,
        eviction_max_open_topics: int = 10,
    ):
        self._state = state or AWMState()
        self._eviction_max_open_topics = eviction_max_open_topics

    @property
    def state(self) -> AWMState:
        return self._state

    def apply(
        self,
        commands: HarvesterLLMOutput,
        current_chunk: int,
        on_resolved: Callable[[AWMTopic, ResolveCommand], None],
    ) -> None:
        """Применяет команды LLM к AWM. on_resolved — колбэк для выброса в staging."""

        self._apply_resolve(commands, on_resolved)
        self._apply_update(commands, current_chunk)
        self._apply_create(commands, current_chunk)
        self._evict_stale(current_chunk, on_resolved)

    def _apply_resolve(
        self,
        commands: HarvesterLLMOutput,
        on_resolved: Callable[[AWMTopic, ResolveCommand], None],
    ) -> None:
        for cmd in commands.resolve:
            topic = self._find(cmd.topic_id)
            if topic is None:
                continue
            topic.status = AWMStatus.RESOLVED
            on_resolved(topic, cmd)
            self._state.active_topics.remove(topic)

    def _apply_update(
        self,
        commands: HarvesterLLMOutput,
        current_chunk: int,
    ) -> None:
        for cmd in commands.update:
            topic = self._find(cmd.topic_id)
            if topic is None:
                continue
            topic.status = cmd.new_status
            topic.last_updated_chunk = current_chunk
            if cmd.new_value:
                topic.current_value = cmd.new_value
            if cmd.new_question:
                topic.unresolved_questions.append(cmd.new_question)
            topic.evidence_backlog.append(cmd.evidence)

    def _apply_create(
        self,
        commands: HarvesterLLMOutput,
        current_chunk: int,
    ) -> None:
        for cmd in commands.create:
            # защита от дублей: та же scope+property уже есть в AWM
            existing = self._find_by_scope_property(cmd.scope, cmd.property)
            if existing:
                existing.current_value = cmd.value
                existing.last_updated_chunk = current_chunk
                existing.evidence_backlog.append(cmd.evidence)
            else:
                self._state.active_topics.append(AWMTopic(
                    scope=cmd.scope,
                    property=cmd.property,
                    current_value=cmd.value,
                    status=cmd.status,
                    last_updated_chunk=current_chunk,
                    evidence_backlog=[cmd.evidence],
                ))

    def _evict_stale(
        self,
        current_chunk: int,
        on_resolved: Callable[[AWMTopic, ResolveCommand], None],
    ) -> None:
        open_topics = [
            t for t in self._state.active_topics
            if t.status != AWMStatus.RESOLVED
        ]
        if len(open_topics) <= self._eviction_max_open_topics:
            return

        to_evict = [
            t for t in open_topics
            if current_chunk - t.last_updated_chunk > EVICTION_STALENESS_THRESHOLD
        ]
        for topic in to_evict:
            topic.status = AWMStatus.STALE
            # выбрасываем как есть — лучше неполный факт, чем потеря
            on_resolved(topic, ResolveCommand(
                topic_id=topic.topic_id,
                final_value=topic.current_value,
                evidence=topic.evidence_backlog[-1] if topic.evidence_backlog else Evidence(
                    chunk_index=topic.last_updated_chunk,
                    quote="[EVICTED: no final evidence]",
                ),
            ))
            self._state.active_topics.remove(topic)

    def _find(self, topic_id: str) -> AWMTopic | None:
        return next((t for t in self._state.active_topics if t.topic_id == topic_id), None)

    def _find_by_scope_property(self, scope: str, prop: str) -> AWMTopic | None:
        return next(
            (t for t in self._state.active_topics
             if t.scope.lower() == scope.lower() and t.property.lower() == prop.lower()),
            None,
        )

    def render_for_prompt(self) -> str:
        """Компактное представление AWM для вставки в промпт."""
        if not self._state.active_topics:
            return "(пусто)"
        lines = []
        for t in self._state.active_topics:
            lines.append(
                f"ID: {t.topic_id} | {t.status} | "
                f"{t.scope} / {t.property} | "
                f"Текущее: {t.current_value}"
            )
        return "\n".join(lines)
