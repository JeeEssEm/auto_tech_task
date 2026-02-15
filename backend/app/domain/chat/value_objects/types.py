import enum


class ChatTemplate(enum.StrEnum):
    GOST19 = "gost19"
    FREE = "free"
    IT_PROJECT = "it_project"
    CONSTRUCTION_PROJECT = "construction_project"
    ENGINEERING_PROJECT = "engineering_project"


class MessageSender(enum.StrEnum):
    USER = "user"
    LLM = "LLM"
