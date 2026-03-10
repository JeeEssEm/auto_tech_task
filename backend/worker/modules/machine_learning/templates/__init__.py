from .base import (
    BaseTemplate, ContentNode, FieldGap, FieldConflict, ValidationResult, TZResult,
)
from .gost import GostTemplate
from .household import HouseholdTemplate
from .it_project import ITProjectTemplate
from .construction import ConstructionTemplate
from .engineering import EngineeringTemplate
from backend.worker.modules.machine_learning.schemas.enums import TemplateType

TEMPLATE_REGISTRY: dict[TemplateType, type[BaseTemplate]] = {
    TemplateType.GOST19: GostTemplate,
    TemplateType.FREE: HouseholdTemplate,
    TemplateType.IT_PROJECT: ITProjectTemplate,
    TemplateType.CONSTRUCTION_PROJECT: ConstructionTemplate,
    TemplateType.ENGINEERING_PROJECT: EngineeringTemplate,
}


def get_template_class(template_type: TemplateType) -> type[BaseTemplate]:
    return TEMPLATE_REGISTRY[template_type]
