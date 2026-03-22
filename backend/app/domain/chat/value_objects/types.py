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
    CONFLICT_REQUIRES_INPUT = "CONFLICT_REQUIRES_INPUT"
    SECTION_AUDIT_FAILED = "SECTION_AUDIT_FAILED"
    PARSING_STATUS = "PARSING_STATUS"
    EXPORT_READY = "EXPORT_READY"
    ERROR = "ERROR"


class ParsingStatus(enum.StrEnum):
    PENDING = "PENDING"
    IN_PROCESS = "IN_PROCESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class GenerationStatus(enum.StrEnum):
    ANALYZING_DATA = "ANALYZING_DATA"
    BUILDING_GRAPH = "BUILDING_GRAPH"
    MERGING_DATA_SOURCES = "MERGING_DATA_SOURCES"
    VERIFYING_DATA = "VERIFYING_DATA"


class GenerationRunStatus(enum.StrEnum):
    PENDING = "PENDING"
    INGESTING = "INGESTING"
    COMPILING = "COMPILING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SubscriptionTier(enum.StrEnum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UsageAction(enum.StrEnum):
    GENERATE_TZ = "generate_tz"
    PARSE_FILE = "parsed_files"
    CREATE_CHAT = "create_chat"
