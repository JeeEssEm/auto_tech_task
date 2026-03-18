import datetime
from typing import Optional, Literal
from uuid import UUID

from backend.worker.modules.llm_pipeline.templates.catalog import TEMPLATES
from backend.worker.modules.llm_pipeline.templates.template import (
    TemplateBlock, DocumentBlock, BlockMeta,
    DocumentStructure
)


def _template_block_to_document_block(
    tb: TemplateBlock,
    template_id: str,
    parent_id: Optional[UUID] = None,
) -> DocumentBlock:
    """
    Рекурсивно превращает TemplateBlock → DocumentBlock.
    Связь сохраняется через meta.template_block_id.
    """
    block = DocumentBlock(
        parent_id=parent_id,
        title=tb.title,
        level=tb.level,
        sort_order=tb.sort_order,
        status="draft",
        meta=BlockMeta(
            origin="template",
            template_id=template_id,
            template_block_id=tb.template_block_id,
            context_hint=tb.context_hint,
        ),
    )
    block.subsections = [
        _template_block_to_document_block(child, template_id, parent_id=block.id)
        for child in tb.subsections
    ]
    return block


def create_document_from_template(
    project_id: int,
    template_id: str,
) -> DocumentStructure:
    """
    Главная фабрика. Принимает ID шаблона → отдаёт пустую DocumentStructure.
    После этого Архитектор заполняет content_md из GKG.
    """
    template = TEMPLATES.get(template_id)
    if template is None:
        raise ValueError(f"Шаблон '{template_id}' не найден. Доступны: {list(TEMPLATES)}")

    blocks = [
        _template_block_to_document_block(tb, template_id)
        for tb in template.blocks
    ]

    return DocumentStructure(
        project_id=project_id,
        template_id=template_id,
        is_template_strict=True,   # снимается после первой генерации
        blocks=blocks,
    )


def create_empty_document(project_id: int) -> DocumentStructure:
    """
    Для случая когда пользователь начинает с чистого листа.
    Архитектор сам предложит блоки на основе GKG (origin='ai_suggested').
    """
    return DocumentStructure(
        project_id=project_id,
        template_id=None,
        is_template_strict=False,
        blocks=[],
    )


def add_user_block(
    doc: DocumentStructure,
    title: str,
    level: Literal[1, 2, 3],
    parent_id: Optional[int] = None,
) -> DocumentBlock:
    """
    Пользователь вручную добавляет блок.
    Архитектор затем ищет данные для него по title, а не по context_hint.
    """
    siblings = (
        _find_block(doc, parent_id).subsections
        if parent_id else doc.blocks
    )
    new_block = DocumentBlock(
        parent_id=parent_id,
        title=title,
        level=level,
        sort_order=len(siblings),
        status="draft",
        meta=BlockMeta(
            origin="user",
            # context_hint нет — Архитектор использует title как поисковый запрос
        ),
    )
    siblings.append(new_block)
    doc.updated_at = datetime.datetime.now()
    return new_block


def _find_block(doc: DocumentStructure, block_id: UUID) -> DocumentBlock:
    """Поиск блока по ID в дереве (DFS)."""
    def _search(blocks: list[DocumentBlock]) -> Optional[DocumentBlock]:
        for b in blocks:
            if b.id == block_id:
                return b
            found = _search(b.subsections)
            if found:
                return found
        return None

    result = _search(doc.blocks)
    if result is None:
        raise ValueError(f"Блок {block_id} не найден в документе")
    return result
