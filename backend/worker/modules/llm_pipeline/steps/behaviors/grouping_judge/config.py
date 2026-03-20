from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict, BaseSettings

from backend.worker.modules.llm_pipeline.abstractions.base_config import BaseConfigSettings


class GroupingJudgeSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LLM_PIPELINE_V3_GROUPING_JUDGE_",
        extra="ignore",
    )
    judge_concurrency: int = 5
    semantic_threshold: float = 0.05
    temperature: float = 0.1
