from pydantic import BaseModel


class OpenAIChatSettings(BaseModel):
    base_url: str
    api_key: str | None = None
    temperature: float = 0.0
    max_tokens: int = 1024
    timeout_seconds: float = 30.0
    max_attempts: int = 4
    log_path: str = "llm.log"
