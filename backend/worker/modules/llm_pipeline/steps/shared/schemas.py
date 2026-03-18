import datetime

from pydantic import BaseModel


class ConversationSummary(BaseModel):
    decisions: list[str]
    rejected_options: list[str]
    open_questions: list[str]
    last_updated_at: datetime.datetime
