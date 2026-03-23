from typing import Any

from pydantic import BaseModel, Field


class RunFullPipelineRequest(BaseModel):
    """Запуск полного пайплайна первичной генерации ТЗ."""
    attachment_ids: list[str] = Field(
        description="ID уже распарсенных вложений, привязанных к чату",
    )
    template_type: str | None = Field(
        default=None,
        description="Шаблон ТЗ (если не передан, берется шаблон чата)",
    )
    comment: str | None = Field(
        default=None,
        description="Опциональный комментарий к первичной генерации",
    )


class UpdateTZRequest(BaseModel):
    """Обновление существующего ТЗ: догрузка файлов и/или глобальный комментарий."""
    new_attachment_ids: list[str] = Field(
        default_factory=list,
        description="ID новых распарсенных вложений",
    )
    comment: str | None = Field(
        default=None,
        description="Глобальный комментарий пользователя (например, 'Сделай ТЗ строже')",
    )


class RegenerateBlockRequest(BaseModel):
    """Перегенерация конкретного блока ТЗ."""
    block_id: str | None = Field(
        default=None,
        description="Идентификатор блока для перегенерации",
    )
    field_path: str | None = Field(
        default=None,
        description="Совместимость со старым контрактом: путь к блоку",
    )
    instruction: str | None = Field(
        default=None,
        description="Инструкция пользователя (например, 'сделай покороче')",
    )


class ResolveConflictRequest(BaseModel):
    """Разрешение pending-конфликта пользователем."""
    action_id: str = Field(description="ID pending_action")
    resolution: str = Field(description="Выбранный вариант или произвольный ответ")


class GenerateCustomBlockRequest(BaseModel):
    """Генерация/заполнение кастомного или пустого блока."""
    field_path: str = Field(
        description="Путь к блоку в dot-notation",
    )
    custom_topic: str = Field(
        description="Тема для генерации (например, 'Требования к анимациям')",
    )


class ManualEditBlockRequest(BaseModel):
    """Ручное редактирование блока ТЗ."""
    field_path: str = Field(
        description="Путь к полю в dot-notation (например, 'general.purpose')",
    )
    value: Any = Field(
        description="Новое значение поля",
    )


class ExportTZRequest(BaseModel):
    """Экспорт ТЗ в файл."""
    result_key: str = Field(
        description="Ключ результата генерации в S3",
    )
    format: str = Field(
        description="Формат экспорта: markdown, word, pdf",
    )


class DocumentSectionPayload(BaseModel):
    """Секция ТЗ для полного сохранения структуры документа."""
    section_id: str | None = Field(
        default=None,
        description="Идентификатор секции (может быть пустым для новых секций)",
    )
    title: str = Field(description="Заголовок секции")
    level: int = Field(default=1, description="Уровень вложенности секции")
    content_md: str = Field(default="", description="Содержимое секции в markdown")
    required: bool = Field(default=True, description="Обязательность секции")
    context_hint: str | None = Field(default=None, description="Контекстная подсказка")
    is_manual: bool = Field(default=True, description="Секция создана/изменена вручную")


class UpdateSectionsRequest(BaseModel):
    """Полное обновление секций ТЗ (порядок, вложенность, названия, контент)."""
    sections: list[DocumentSectionPayload] = Field(
        description="Полный список секций документа в требуемом порядке",
    )
