from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import SettingsConfigDict, BaseSettings


class BaseConfigSettings(BaseSettings):
    provider: Literal["local", "cloud"] = "local"
    base_url: str
    model: str = "gpt-oss:20b"
    api_key: str | None = None
    max_tokens: int = Field(default=16348, gt=32)
    timeout_seconds: float = Field(default=20.0, gt=0.1, le=120.0)

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        aliases = {
            "ollama": "local",
            "openai": "cloud",
            "api": "cloud",
        }
        return aliases.get(normalized, normalized)
