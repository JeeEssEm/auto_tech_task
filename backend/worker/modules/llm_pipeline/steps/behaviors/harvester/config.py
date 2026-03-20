from pydantic import Field
from pydantic_settings import SettingsConfigDict

from backend.worker.modules.llm_pipeline.abstractions.base_config import BaseConfigSettings


class HarvesterSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LLM_PIPELINE_V3_HARVESTER_",
        extra="ignore",
    )

    max_self_correction_retries: int = Field(default=2, ge=0, le=5)
    eviction_max_open_topics: int = Field(default=10, ge=1, le=100)
