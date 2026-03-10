from pydantic import BaseModel


class UserProfile(BaseModel):
    id: int
    email: str
    login: str
    firstname: str
    middlename: str | None
    lastname: str
    role: str
    is_active: bool
    subscription_tier: str


class UsageLimits(BaseModel):
    generate_tz: int
    parse_files: int
    create_chat: int


class TodayUsage(BaseModel):
    generate_tz: int = 0
    parsed_files: int = 0


class UsageStats(BaseModel):
    tier: str
    today: TodayUsage
    total_chats: int
    limits: UsageLimits
