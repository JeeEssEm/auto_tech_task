from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbedderSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LLM_PIPELINE_V3_EMBEDDER_",
        extra="ignore",
    )

    model: str = "intfloat/multilingual-e5-large"
    batch_size: int = 32
    concurrency: int = 4
