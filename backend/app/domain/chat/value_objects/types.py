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


class EventType(enum.StrEnum):
    LLM_ANSWER = "LLM_ANSWER"
    GENERATION_STATUS = "GENERATION_STATUS"
    PARSING_STATUS = "PARSING_STATUS"
    ERROR = "ERROR"


class ParsingStatus(enum.StrEnum):
    PENDING = "PENDING"
    IN_PROCESS = "IN_PROCESS"
    SUCCESSFULLY_ENDED = "SUCCESSFULLY_ENDED"
    FAILED = "FAILED"
