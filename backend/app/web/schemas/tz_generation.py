from typing import Any

from pydantic import BaseModel, Field


class RunFullPipelineRequest(BaseModel):
    """Запуск полного пайплайна первичной генерации ТЗ."""
    attachment_ids: list[str] = Field(
        description="ID уже распарсенных вложений, привязанных к чату",
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
    field_path: str = Field(
        description="Путь к блоку в dot-notation (например, 'technical.tech_stack')",
    )
    instruction: str | None = Field(
        default=None,
        description="Инструкция пользователя (например, 'сделай покороче')",
    )


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


class ContentNodePayload(BaseModel):
    """Подпункт ТЗ, созданный пользователем."""
    id: str = Field(description="Уникальный идентификатор")
    title: str = Field(default="", description="Заголовок подпункта")
    content: str = Field(default="", description="Содержимое (markdown)")
    children: list["ContentNodePayload"] = Field(
        default_factory=list, description="Дочерние подпункты (макс. 3 уровня)",
    )


ContentNodePayload.model_rebuild()


class UpdateCustomSectionsRequest(BaseModel):
    """Обновление пользовательских подпунктов секции ТЗ."""
    section_key: str = Field(
        description="Ключ секции (например, 'general', 'functional')",
    )
    sections: list[ContentNodePayload] = Field(
        description="Полное дерево подпунктов для секции",
    )
