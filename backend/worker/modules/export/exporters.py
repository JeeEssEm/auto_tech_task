"""
Стратегии экспорта ТЗ: Markdown, PDF, DOCX.

Паттерн Strategy — каждый класс реализует единый интерфейс ``ITzExporter``.

Выбор библиотек
---------------
- **PDF — WeasyPrint**:
    Преимущества: CSS-стилизация, полная поддержка Unicode/кириллицы, таблицы.
    Системные зависимости (Docker): ``libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0``
    Dockerfile:
        ``RUN apt-get update && apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0``

- **DOCX — htmldocx (обёртка над python-docx)**:
    Конвертирует HTML → python-docx элементы (параграфы, списки, таблицы, inline-стили).
    Зависимости: ``pip install htmldocx`` (чисто Python, без системных пакетов).

- **Markdown → HTML — библиотека ``markdown``**:
    Стандартный конвертер с расширениями ``tables``, ``fenced_code``, ``toc``.
"""

from __future__ import annotations

import io
import os
from abc import ABC, abstractmethod
from pathlib import Path

import markdown

# ---------------------------------------------------------------------------
# Базовый интерфейс (Strategy)
# ---------------------------------------------------------------------------

class ITzExporter(ABC):
    """Интерфейс экспортёра ТЗ.

    Принимает готовый Markdown (Master-документ), возвращает байты файла.
    """

    @abstractmethod
    async def export(self, markdown_content: str) -> bytes:
        ...

    @property
    @abstractmethod
    def content_type(self) -> str:
        ...

    @property
    @abstractmethod
    def file_extension(self) -> str:
        ...


# ---------------------------------------------------------------------------
# Общий хелпер: Markdown → HTML
# ---------------------------------------------------------------------------

_MD_EXTENSIONS = ["tables", "fenced_code", "toc", "sane_lists", "nl2br"]

# Базовый CSS для HTML-представления ТЗ (используется в PDF и DOCX)
_BASE_CSS = """\
@page {
    size: A4;
    margin: 20mm 15mm 20mm 15mm;
}
body {
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
}
h1 { font-size: 20pt; margin-top: 0; margin-bottom: 12pt; border-bottom: 2px solid #333; padding-bottom: 6pt; }
h2 { font-size: 16pt; margin-top: 18pt; margin-bottom: 8pt; color: #222; }
h3 { font-size: 13pt; margin-top: 14pt; margin-bottom: 6pt; color: #333; }
h4, h5, h6 { font-size: 11pt; margin-top: 10pt; margin-bottom: 4pt; font-weight: bold; }
p { margin: 4pt 0; }
ul, ol { margin: 4pt 0 4pt 18pt; }
li { margin: 2pt 0; }
table { width: 100%; border-collapse: collapse; margin: 8pt 0; }
th, td { border: 1px solid #999; padding: 6pt 8pt; text-align: left; vertical-align: top; }
th { background: #f0f0f0; font-weight: bold; }
code { font-family: Consolas, monospace; font-size: 10pt; background: #f5f5f5; padding: 1pt 3pt; border-radius: 3pt; }
pre { background: #f5f5f5; padding: 8pt; border-radius: 4pt; overflow-x: auto; }
pre code { background: none; padding: 0; }
strong { font-weight: bold; }
em { font-style: italic; }
"""



# ---------------------------------------------------------------------------
# 1. MarkdownExporter
# ---------------------------------------------------------------------------

class MarkdownExporter(ITzExporter):
    """Экспорт в Markdown — просто возвращает закодированную строку."""

    async def export(self, markdown_content: str) -> bytes:
        return markdown_content.encode("utf-8")

    @property
    def content_type(self) -> str:
        return "text/markdown; charset=utf-8"

    @property
    def file_extension(self) -> str:
        return "md"


# ---------------------------------------------------------------------------
# 2. PdfExporter (WeasyPrint)
# ---------------------------------------------------------------------------
class PdfExporter(ITzExporter):
    """Экспорт в PDF через библиотеку markdown-pdf.
    Использует PyMuPDF: не конфликтует с правами Windows Temp и отлично работает с кириллицей.
    Зависимости: pip install markdown-pdf
    """

    async def export(self, markdown_content: str) -> bytes:
        try:
            from markdown_pdf import MarkdownPdf, Section
        except ImportError as e:
            raise RuntimeError("Установите зависимость: pip install markdown-pdf") from e

        # CSS-стили для настройки отображения в PDF
        pdf_css = """
        body {
            font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #1a1a1a;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #222222;
            margin-bottom: 8pt;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10pt;
        }
        th, td {
            border: 1px solid #666666;
            padding: 6px;
        }
        th {
            background-color: #f0f0f0;
            font-weight: bold;
        }
        pre {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
        }
        del {
            text-decoration: line-through;
        }
        """

        # Создаем PDF-документ (toc_level отвечает за уровень заголовков в боковом оглавлении PDF)
        pdf = MarkdownPdf(toc_level=2)

        # Добавляем markdown как секцию.
        # Обратите внимание: markdown-pdf сама парсит Markdown,
        # поэтому передаем сырой текст, а не HTML.
        pdf.add_section(Section(markdown_content, toc=False), user_css=pdf_css)

        # Сохраняем результат напрямую в байтовый буфер
        buf = io.BytesIO()
        pdf.save(buf)

        return buf.getvalue()

    @property
    def content_type(self) -> str:
        return "application/pdf"

    @property
    def file_extension(self) -> str:
        return "pdf"

# ---------------------------------------------------------------------------
# 3. DocxExporter (htmldocx + python-docx)
# ---------------------------------------------------------------------------

class DocxExporter(ITzExporter):
    """Экспорт Markdown → HTML → DOCX через htmldocx.

    htmldocx корректно переносит inline-стили (bold, italic),
    маркированные/нумерованные списки и таблицы в стили Word.
    Зависимости: pip install htmldocx python-docx
    """

    async def export(self, markdown_content: str) -> bytes:
        try:
            from htmldocx import HtmlToDocx  # type: ignore[import-untyped]
        except ImportError as e:
            raise RuntimeError(
                "htmldocx не установлен. Установите: pip install htmldocx"
            ) from e

        html_body = markdown.markdown(markdown_content, extensions=_MD_EXTENSIONS)
        converter = HtmlToDocx()
        docx_doc = converter.parse_html_string(html_body)

        for table in docx_doc.tables:
            table.style = 'Table Grid'

        buf = io.BytesIO()
        docx_doc.save(buf)
        return buf.getvalue()

    @property
    def content_type(self) -> str:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    @property
    def file_extension(self) -> str:
        return "docx"


# ---------------------------------------------------------------------------
# Фабрика / реестр экспортёров
# ---------------------------------------------------------------------------

_EXPORTER_REGISTRY: dict[str, type[ITzExporter]] = {
    "markdown": MarkdownExporter,
    "word": DocxExporter,
    "pdf": PdfExporter,
}


def get_exporter(format_name: str) -> ITzExporter:
    """Возвращает экземпляр экспортёра по имени формата.

    Raises ``ValueError`` для неизвестного формата.
    """
    cls = _EXPORTER_REGISTRY.get(format_name)
    if cls is None:
        supported = ", ".join(sorted(_EXPORTER_REGISTRY))
        raise ValueError(
            f"Неизвестный формат экспорта: '{format_name}'. "
            f"Поддерживаемые: {supported}"
        )
    return cls()
