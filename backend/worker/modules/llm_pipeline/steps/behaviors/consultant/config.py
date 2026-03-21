from pydantic import Field
from pydantic_settings import SettingsConfigDict

from backend.worker.modules.llm_pipeline.abstractions.base_config import BaseConfigSettings


class ConsultantSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LLM_PIPELINE_V3_CONSULTANT_",
        extra="ignore",
    )
    max_tool_calls: int = Field(default=6, ge=1, le=15)
    temperature: float = 0.2
