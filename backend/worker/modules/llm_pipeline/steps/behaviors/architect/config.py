from pydantic import Field
from pydantic_settings import SettingsConfigDict

from backend.worker.modules.llm_pipeline.abstractions.base_config import BaseConfigSettings


class ArchitectSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LLM_PIPELINE_V3_ARCHITECT_",
        extra="ignore",
    )
    max_consistency_retries: int = 2
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_tool_calls: int = Field(default=12, ge=1, le=20)
