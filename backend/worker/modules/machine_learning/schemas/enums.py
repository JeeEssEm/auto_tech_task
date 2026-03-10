import enum


class TemplateType(enum.StrEnum):
    GOST19 = "gost19"
    FREE = "free"
    IT_PROJECT = "it_project"
    CONSTRUCTION_PROJECT = "construction_project"
    ENGINEERING_PROJECT = "engineering_project"
