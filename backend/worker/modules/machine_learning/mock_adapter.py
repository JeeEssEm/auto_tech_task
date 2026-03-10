from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, List, Optional

from backend.worker.modules.machine_learning.interface import (
    ITZPipelineAdapter,
    ProgressNotifier,
    DataSource,
    TZResult,
    ConflictResolution,
)
from backend.worker.modules.machine_learning.templates.base import (
    FieldConflict,
    ValidationResult,
)
from backend.worker.modules.machine_learning.templates.it_project import (
    ITProjectTemplate,
    GeneralDescription,
    FunctionalRequirements,
    UserRole,
    UseCase,
    TechStack,
    TechnicalRequirements,
    DevelopmentStages,
    DevelopmentPhase,
    AcceptanceCriteria,
)


class MockITZPipelineAdapter:
    """
    Мок-реализация ITZPipelineAdapter.

    Имитирует работу LLM-пайплайна с помощью asyncio.sleep().
    Предназначена для тестирования UI (статусы, прогресс-бары, итоговое ТЗ),
    пока разрабатывается реальный LLM-движок.

    В будущем достаточно заменить на RealLLMPipelineAdapter —
    бизнес-логика фоновых задач и персистенции не изменится.
    """

    def __init__(self) -> None:
        self._notifier: ProgressNotifier | None = None
        self._sources: list[DataSource] = []
        self._state: dict[str, Any] = {}

    # --- Управление состоянием ---

    def attach_notifier(self, notifier: ProgressNotifier) -> None:
        self._notifier = notifier

    def save_state(self) -> Dict[str, Any]:
        return {
            "sources": [s.model_dump() for s in self._sources],
            "internal_state": self._state,
        }

    @classmethod
    def load_state(cls, state: Dict[str, Any]) -> MockITZPipelineAdapter:
        adapter = cls()
        adapter._sources = [DataSource(**s) for s in state.get("sources", [])]
        adapter._state = state.get("internal_state", {})
        return adapter

    # --- Приватные хелперы ---

    async def _notify(self, event_name: str, payload: Dict[str, Any]) -> None:
        if self._notifier is not None:
            await self._notifier(event_name, payload)

    @staticmethod
    async def _simulate_delay(min_sec: float = 1.5, max_sec: float = 3.5) -> None:
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    # --- Основной пайплайн ---

    async def ingest_sources(self, sources: List[DataSource]) -> List[FieldConflict]:
        self._sources.extend(sources)

        await self._notify("extracting", {
            "message": "Извлекаем сущности из источников...",
            "progress": 10,
        })
        await self._simulate_delay(2, 4)

        await self._notify("analyzing", {
            "message": "Анализируем структуру данных...",
            "progress": 40,
        })
        await self._simulate_delay(1.5, 3)

        await self._notify("conflict_check", {
            "message": "Ищем противоречия между источниками...",
            "progress": 70,
        })
        await self._simulate_delay(1, 2)

        await self._notify("ingest_done", {
            "message": "Обработка источников завершена",
            "progress": 100,
        })

        return [
            FieldConflict(
                field_path="general.budget",
                field_name="Бюджет проекта",
                options=["100 000 руб.", "200 000 руб."],
                description="Противоречивые данные о бюджете из разных источников",
                section="general",
            ),
        ]

    async def compile_document(self) -> TZResult:
        await self._notify("compiling", {
            "message": "Собираем структуру ТЗ...",
            "progress": 10,
        })
        await self._simulate_delay(2, 3)

        await self._notify("filling_sections", {
            "message": "Заполняем разделы шаблона...",
            "progress": 40,
        })
        await self._simulate_delay(2, 4)

        await self._notify("validating", {
            "message": "Валидируем заполненность полей...",
            "progress": 80,
        })
        await self._simulate_delay(1, 2)

        template = self._build_mock_template()
        validation = template.validate_completeness()

        await self._notify("compile_done", {
            "message": "Сборка ТЗ завершена",
            "progress": 100,
        })

        return TZResult(
            template_type="it_project",
            document=template,
            validation=validation,
        )

    # --- Точечные изменения (заглушки) ---

    async def regenerate_block(
        self,
        field_path: str,
        instruction: Optional[str] = None,
    ) -> TZResult:
        await self._notify("regenerating", {
            "message": f"Перегенерируем блок «{field_path}»...",
            "progress": 50,
        })
        await self._simulate_delay(2, 4)

        template = self._build_mock_template()
        return TZResult(
            template_type="it_project",
            document=template,
            validation=template.validate_completeness(),
        )

    async def apply_global_comment(self, comment: str) -> TZResult:
        await self._notify("applying_comment", {
            "message": f"Применяем комментарий: «{comment[:60]}»...",
            "progress": 50,
        })
        await self._simulate_delay(2, 5)

        template = self._build_mock_template()
        return TZResult(
            template_type="it_project",
            document=template,
            validation=template.validate_completeness(),
        )

    async def generate_custom_block_content(
        self,
        field_path: str,
        custom_topic: str,
    ) -> TZResult:
        await self._notify("generating_block", {
            "message": f"Генерируем контент для «{custom_topic}»...",
            "progress": 50,
        })
        await self._simulate_delay(2, 4)

        template = self._build_mock_template()
        return TZResult(
            template_type="it_project",
            document=template,
            validation=template.validate_completeness(),
        )

    # --- Интерактив ---

    async def resolve_conflicts(self, resolutions: List[ConflictResolution]) -> None:
        for resolution in resolutions:
            self._state[resolution.field_path] = resolution.chosen_value

    async def answer_gaps(self, answers: Dict[str, str]) -> TZResult:
        self._state.update(answers)
        template = self._build_mock_template()
        return TZResult(
            template_type="it_project",
            document=template,
            validation=template.validate_completeness(),
        )

    # --- Ручное вмешательство ---

    def apply_manual_edit(self, field_path: str, value: Any) -> None:
        self._state[f"manual:{field_path}"] = value

    # --- Генерация мок-данных ---

    @staticmethod
    def _build_mock_template() -> ITProjectTemplate:
        source_text = "данные из пользовательских источников"
        return ITProjectTemplate(
            general=GeneralDescription(
                purpose=f"Автоматизированная система управления проектами ({source_text})",
                analogues=["Jira", "Trello", "Asana"],
                expected_outcome="Веб-приложение для управления задачами с интеграцией календаря",
            ),
            functional=FunctionalRequirements(
                roles=[
                    UserRole(
                        name="Администратор",
                        capabilities=["Управление пользователями", "Настройка системы"],
                    ),
                    UserRole(
                        name="Менеджер проекта",
                        capabilities=["Создание задач", "Назначение исполнителей", "Отслеживание прогресса"],
                    ),
                ],
                use_cases=[
                    UseCase(
                        name="Создание проекта",
                        steps=[
                            "Менеджер нажимает «Новый проект»",
                            "Заполняет форму с параметрами",
                            "Система создаёт проект и уведомляет участников",
                        ],
                    ),
                ],
                modules=["Дашборд", "Канбан-доска", "Календарь", "Отчёты"],
            ),
            technical=TechnicalRequirements(
                tech_stack=TechStack(
                    frontend="React 18 + TypeScript",
                    backend="FastAPI + Python 3.12",
                    database="PostgreSQL 16",
                    other=["Redis (кэш / очереди)", "MinIO (S3-совместимое хранилище)"],
                ),
            ),
            stages=DevelopmentStages(
                mvp=DevelopmentPhase(
                    name="MVP",
                    deadline="2 месяца",
                    features=["Авторизация", "Управление задачами", "Канбан-доска"],
                ),
                release=DevelopmentPhase(
                    name="Релиз v1.0",
                    deadline="4 месяца",
                    features=["Отчёты", "Интеграции", "Мобильная адаптация"],
                ),
            ),
            acceptance=AcceptanceCriteria(
                testing=["Unit-тесты покрывают ≥80% бизнес-логики", "E2E-тесты основных сценариев"],
                documentation=["Swagger/OpenAPI спецификация", "Руководство пользователя"],
            ),
        )
