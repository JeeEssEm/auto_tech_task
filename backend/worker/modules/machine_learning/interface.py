from typing import Protocol, Callable, Awaitable, Any, Optional, Dict, List
from pydantic import BaseModel, Field

from backend.worker.modules.machine_learning.templates import BaseTemplate, ValidationResult, ContentNode

# Сигнатура асинхронного коллбэка для отправки прогресса по WebSockets / SSE
# event_name: 'extracting', 'compiling', 'conflict_detected', 'done'
# payload: dict с метаданными (процент, кол-во токенов, фрагменты)
ProgressNotifier = Callable[[str, Dict[str, Any]], Awaitable[None]]


class DataSource(BaseModel):
    id: str
    type: str
    content: str


class ConflictResolution(BaseModel):
    field_path: str
    chosen_value: Any # Значение, которое выбрал пользователь из предложенных LLM

class TZResult(BaseModel):
    template_type: str
    document: BaseTemplate
    validation: "ValidationResult"
    custom_sections: dict[str, list[ContentNode]] = Field(
        default_factory=dict,
        description="Пользовательские подпункты, ключ — section_key",
    )


class ITZPipelineAdapter(Protocol):
    """
    Контракт взаимодействия бэкенда и LLM-пайплайна генерации ТЗ.
    Имплементация этого класса должна быть сериализуемой (save/load_state),
    так как процесс разорван во времени (HTTP-запросы).
    """

    # --- 1. Управление состоянием (Инфраструктура) ---

    def save_state(self) -> Dict[str, Any]:
        """Сериализует весь текущий контекст (источники, промпты, текущий JSON) для БД."""
        ...

    @classmethod
    def load_state(cls, state: Dict[str, Any]) -> "ITZPipelineAdapter":
        """Восстанавливает пайплайн из БД перед выполнением следующей таски."""
        ...

    def attach_notifier(self, notifier: ProgressNotifier) -> None:
        """Привязывает коллбэк для уведомления пользователя о прогрессе."""
        ...


    # --- 2. Работа с источниками (Инварианты: Создание чата, Догрузка файлов) ---

    async def ingest_sources(self, sources: List[DataSource]) -> List["FieldConflict"]:
        """
        Асинхронно обрабатывает новые источники.
        LLM извлекает факты, маппит на шаблон.
        Если это догрузка (уже есть ТЗ), LLM ищет противоречия со старым контекстом.
        Возвращает список конфликтов, если новые данные противоречат старым.
        """
        ...


    # --- 3. Генерация и компиляция (Инвариант: Получение итогового ТЗ/Экспорт) ---

    async def compile_document(self) -> TZResult:
        """
        Собирает все извлеченные знания в итоговый Pydantic-объект шаблона.
        Валидирует пустоты (gaps). Триггерит `notifier` по ходу сборки блоков.
        """
        ...


    # --- 4. Точечные изменения LLM (Инварианты: Перегенерация, Комментарии) ---

    async def regenerate_block(
        self,
        field_path: str,
        instruction: Optional[str] = None
    ) -> TZResult:
        """
        Переписывает конкретный блок (например, 'technical.tech_stack').
        Если передан `instruction` (комментарий пользователя: "сделай короче"), учитывает его.
        LLM обязана учитывать контекст остальных блоков, чтобы не сломать логику.
        """
        ...

    async def apply_global_comment(self, comment: str) -> TZResult:
        """
        Пользователь написал в чат: "Убери все упоминания о мобильной версии".
        LLM-роутер сам решает, какие поля (field_path) в шаблоне нужно пропатчить,
        и обновляет их.
        """
        ...

    async def generate_custom_block_content(
        self,
        field_path: str,
        custom_topic: str
    ) -> TZResult:
        """
        Инвариант: Пользователь добавил блок руками (например, в 'details')
        и просит LLM его заполнить.
        `custom_topic` = "Требования к анимации".
        """
        ...


    # --- 5. Интерактив с пользователем (Разрешение конфликтов и пустот) ---

    async def resolve_conflicts(self, resolutions: List[ConflictResolution]) -> None:
        """
        Применяет выбор пользователя по конфликтующим данным.
        (Например, в аудио: "бюджет 100к", в письме: "бюджет 200к". Юзер выбрал 200к).
        """
        ...

    async def answer_gaps(self, answers: Dict[str, str]) -> TZResult:
        """
        Пользователь через UI ответил на вопросы системы по обязательным пустым полям
        (gaps из ValidationResult). Пайплайн встраивает ответы в ТЗ.
        """
        ...


    # --- 6. Ручное вмешательство (Инвариант: Ручные правки) ---

    def apply_manual_edit(self, field_path: str, value: Any) -> None:
        """
        Пользователь руками поправил текст в UI.
        Пайплайн обновляет свой внутренний стейт и помечает это поле как `is_manual=True`,
        чтобы при глобальных перегенерациях LLM относилась к нему осторожно
        (или вообще не трогала).
        """
        ...
