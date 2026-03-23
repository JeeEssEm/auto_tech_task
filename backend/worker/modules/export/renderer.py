"""
TemplateMarkdownRenderer — рекурсивный рендерер Pydantic-модели (BaseTemplate)
в единую Markdown-строку.

Алгоритм:
  • Рекурсивно обходит все поля модели.
  • Уровень вложенности определяет уровень заголовка (#, ##, ###, …).
  • Заголовок берётся из ``Field(description=...)``.
  • ``List[str]`` → маркированный список.
  • ``str`` (уже содержит Markdown от LLM) — вставляется под заголовком как есть.
  • ``None`` и пустые списки пропускаются.

Дополнительно поддерживается ``render_from_data`` — рендеринг из «сырого» dict,
в котором отдельные поля могут быть заменены на строки после ручного
редактирования пользователем (manual-edit).
"""

from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel
from pydantic.fields import FieldInfo


class TemplateMarkdownRenderer:
    """Рендерит ``BaseTemplate`` (и любого наследника) в Markdown."""

    # Максимальный уровень заголовка (######) по спецификации Markdown
    _MAX_HEADING = 6

    # ------------------------------------------------------------------
    # Публичное API
    # ------------------------------------------------------------------

    def render(self, template, *, title: str | None = None) -> str:
        lines: list[str] = []
        top_title = title or template.__class__.__doc__ or "Техническое задание"
        top_title = top_title.strip().split("\n")[0]
        lines.append(f"# {top_title}")
        lines.append("")

        self._render_model(template, level=2, lines=lines)
        return "\n".join(lines)

    def render_from_data(
        self,
        data: dict[str, Any],
        template_class,
        *,
        title: str | None = None,
    ) -> str:
        """Рендерит Markdown из «сырого» dict + класс шаблона (для описаний полей).

        После ручного редактирования (manual-edit) отдельные поля в JSON
        заменяются с вложенных объектов на plain-строки.  Этот метод
        обрабатывает оба варианта корректно, а ``model_validate`` в таком
        случае упал бы с ``ValidationError``.
        """
        lines: list[str] = []
        top_title = title or template_class.__doc__ or "Техническое задание"
        top_title = top_title.strip().split("\n")[0]
        lines.append(f"# {top_title}")
        lines.append("")

        self._render_dict(data, template_class, level=2, lines=lines)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Рендеринг из Pydantic-модели
    # ------------------------------------------------------------------

    def _render_model(
        self,
        obj: BaseModel,
        level: int,
        lines: list[str],
    ) -> None:
        for name, field_info in obj.model_fields.items():
            value = getattr(obj, name, None)
            heading = self._heading_text(field_info, name)
            self._render_field(value, heading, level, lines, field_info)

    def _render_field(
        self,
        value: Any,
        heading: str,
        level: int,
        lines: list[str],
        field_info: FieldInfo,
    ) -> None:
        # --- None / пустая строка → пропустить ---
        if value is None:
            return
        if isinstance(value, str) and not value.strip():
            return

        # --- Вложенная Pydantic-модель ---
        if isinstance(value, BaseModel):
            if self._is_model_empty(value):
                return
            lines.append(f"{'#' * min(level, self._MAX_HEADING)} {heading}")
            lines.append("")
            self._render_model(value, level + 1, lines)
            return

        # --- Список ---
        if isinstance(value, list):
            if not value:
                return
            # Список Pydantic-моделей
            if value and isinstance(value[0], BaseModel):
                lines.append(f"{'#' * min(level, self._MAX_HEADING)} {heading}")
                lines.append("")
                for item in value:
                    self._render_list_model_item(item, level + 1, lines)
                return
            # Список строк → маркированный список
            lines.append(f"{'#' * min(level, self._MAX_HEADING)} {heading}")
            lines.append("")
            for item in value:
                lines.append(f"- {item}")
            lines.append("")
            return

        # --- Скалярное значение (строка, число, …) ---
        str_value = str(value).strip()
        if not str_value:
            return
        lines.append(f"{'#' * min(level, self._MAX_HEADING)} {heading}")
        lines.append("")
        lines.append(str_value)
        lines.append("")

    def _render_list_model_item(
        self,
        item: BaseModel,
        level: int,
        lines: list[str],
    ) -> None:
        """Рендерит один элемент списка моделей (например, UserRole, UseCase)."""
        # Ищем «имя» элемента по полям name / title
        item_title = None
        for attr in ("name", "title"):
            v = getattr(item, attr, None)
            if v and str(v).strip():
                item_title = str(v).strip()
                break
        if item_title is None:
            item_title = item.__class__.__name__

        lines.append(f"{'#' * min(level, self._MAX_HEADING)} {item_title}")
        lines.append("")

        for name, field_info in item.model_fields.items():
            if name in ("name", "title"):
                continue  # уже в заголовке
            value = getattr(item, name, None)
            heading = self._heading_text(field_info, name)
            # Для полей внутри элемента списка не создаём подзаголовок,
            # а рендерим как bullet / inline
            if isinstance(value, list) and value:
                for v in value:
                    lines.append(f"- {v}")
            elif isinstance(value, str) and value.strip():
                lines.append(f"**{heading}:** {value}")
            elif isinstance(value, BaseModel):
                self._render_model(value, level + 1, lines)
        lines.append("")

    # ------------------------------------------------------------------
    # Рендеринг из «сырого» dict (после manual-edit)
    # ------------------------------------------------------------------

    def _render_dict(
        self,
        data: dict[str, Any],
        model_class: type[BaseModel],
        level: int,
        lines: list[str],
    ) -> None:
        """Обходит dict, используя ``model_class.model_fields`` для описаний."""
        for name, field_info in model_class.model_fields.items():
            value = data.get(name)
            heading = self._heading_text(field_info, name)
            self._render_dict_field(value, heading, level, lines, field_info)

    def _render_dict_field(
        self,
        value: Any,
        heading: str,
        level: int,
        lines: list[str],
        field_info: FieldInfo,
    ) -> None:
        if value is None:
            return

        # --- Строка (включая случай, когда вложенная модель заменена
        #     на markdown-строку после manual-edit) ---
        if isinstance(value, str):
            if not value.strip():
                return
            lines.append(f"{'#' * min(level, self._MAX_HEADING)} {heading}")
            lines.append("")
            lines.append(value.strip())
            lines.append("")
            return

        # --- Вложенный словарь (структура модели сохранилась) ---
        if isinstance(value, dict):
            if self._is_dict_empty(value):
                return
            # Пытаемся определить подкласс модели из аннотации поля
            sub_class = self._resolve_model_class(field_info)
            lines.append(f"{'#' * min(level, self._MAX_HEADING)} {heading}")
            lines.append("")
            if sub_class is not None:
                self._render_dict(value, sub_class, level + 1, lines)
            else:
                # Без метаданных — рендерим ключи-значения как есть
                self._render_plain_dict(value, level + 1, lines)
            return

        # --- Список ---
        if isinstance(value, list):
            if not value:
                return
            lines.append(f"{'#' * min(level, self._MAX_HEADING)} {heading}")
            lines.append("")
            for item in value:
                if isinstance(item, dict):
                    self._render_plain_dict_item(item, level + 1, lines)
                else:
                    lines.append(f"- {item}")
            lines.append("")
            return

        # --- Скаляр ---
        str_value = str(value).strip()
        if str_value:
            lines.append(f"{'#' * min(level, self._MAX_HEADING)} {heading}")
            lines.append("")
            lines.append(str_value)
            lines.append("")

    def _render_plain_dict(
        self,
        data: dict[str, Any],
        level: int,
        lines: list[str],
    ) -> None:
        for key, value in data.items():
            if value is None:
                continue
            heading = key.replace("_", " ").title()
            if isinstance(value, str) and value.strip():
                lines.append(f"{'#' * min(level, self._MAX_HEADING)} {heading}")
                lines.append("")
                lines.append(value.strip())
                lines.append("")
            elif isinstance(value, list) and value:
                lines.append(f"{'#' * min(level, self._MAX_HEADING)} {heading}")
                lines.append("")
                for item in value:
                    lines.append(f"- {item}")
                lines.append("")
            elif isinstance(value, dict):
                if not self._is_dict_empty(value):
                    lines.append(f"{'#' * min(level, self._MAX_HEADING)} {heading}")
                    lines.append("")
                    self._render_plain_dict(value, level + 1, lines)

    def _render_plain_dict_item(
        self,
        item: dict[str, Any],
        level: int,
        lines: list[str],
    ) -> None:
        item_title = item.get("name") or item.get("title")
        if item_title and str(item_title).strip():
            lines.append(f"{'#' * min(level, self._MAX_HEADING)} {item_title}")
            lines.append("")
        for key, value in item.items():
            if key in ("name", "title") and item_title:
                continue
            if value is None:
                continue
            label = key.replace("_", " ").title()
            if isinstance(value, list) and value:
                for v in value:
                    lines.append(f"- {v}")
            elif isinstance(value, str) and value.strip():
                lines.append(f"**{label}:** {value}")
        lines.append("")

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------

    @staticmethod
    def _heading_text(field_info: FieldInfo, fallback: str) -> str:
        desc = field_info.description
        if desc:
            # Убираем суффиксы типа «(optional)» из heading
            clean = desc.replace("(optional)", "").strip()
            return clean if clean else fallback
        return fallback.replace("_", " ").title()

    @staticmethod
    def _resolve_model_class(field_info: FieldInfo) -> type[BaseModel] | None:
        """Пытается извлечь класс Pydantic-модели из аннотации поля."""
        annotation = field_info.annotation
        if annotation is None:
            return None
        # Unwrap Optional / Union
        origin = getattr(annotation, "__origin__", None)
        if origin is not None:
            args = getattr(annotation, "__args__", ())
            for arg in args:
                if isinstance(arg, type) and issubclass(arg, BaseModel):
                    return arg
            return None
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return annotation
        return None

    @staticmethod
    def _is_model_empty(obj: BaseModel) -> bool:
        """Рекурсивно проверяет, что все поля модели пустые."""
        for name in obj.model_fields:
            value = getattr(obj, name, None)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if isinstance(value, list) and not value:
                continue
            if isinstance(value, BaseModel):
                if not TemplateMarkdownRenderer._is_model_empty(value):
                    return False
                continue
            return False
        return True

    @staticmethod
    def _is_dict_empty(data: dict[str, Any]) -> bool:
        for value in data.values():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if isinstance(value, list) and not value:
                continue
            if isinstance(value, dict):
                if not TemplateMarkdownRenderer._is_dict_empty(value):
                    return False
                continue
            return False
        return True
