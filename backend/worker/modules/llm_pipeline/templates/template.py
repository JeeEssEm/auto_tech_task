import datetime
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

OriginType = Literal["template", "user", "ai_suggested"]
BlockStatus = Literal["draft", "generated", "manual", "missing", "locked"]


DomainType = Literal["formal", "free", "it", "construction", "engineering"]


class TemplateBlock(BaseModel):
    """
    Чертёж блока. Не содержит контента — только структуру и подсказки.
    Из него фабрика штампует DocumentBlock с origin='template'.
    """
    template_block_id: str          # стабильный ID внутри шаблона, напр. "sec_db"
    title: str
    level: Literal[1, 2, 3]
    sort_order: int
    context_hint: str               # что искать в GKG для этого блока
    required: bool = True           # если True и данных нет → MISSING, не пропускаем
    subsections: list["TemplateBlock"] = Field(default_factory=list)


class Template(BaseModel):
    template_id: str
    name: str
    domain: DomainType
    version: str
    description: str
    blocks: list[TemplateBlock]


class BlockMeta(BaseModel):
    origin: OriginType
    template_id: Optional[str] = None
    template_block_id: Optional[str] = None   # ← связь с TemplateBlock
    context_hint: Optional[str] = None
    gkg_topic_ids: list[str] = Field(default_factory=list)
    last_generated_at: Optional[datetime.datetime] = None
    pending_action_id: Optional[UUID] = None


class DocumentBlock(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    parent_id: Optional[UUID] = None
    title: str
    level: Literal[1, 2, 3]
    sort_order: int
    content_md: str = ""
    status: BlockStatus = "draft"
    meta: BlockMeta
    subsections: list["DocumentBlock"] = Field(default_factory=list)


class DocumentStructure(BaseModel):
    project_id: int
    template_id: Optional[str] = None
    is_template_strict: bool = False
    blocks: list[DocumentBlock] = Field(default_factory=list)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
