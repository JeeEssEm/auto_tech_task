import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class UvicornSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="UVICORN_")

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = os.cpu_count()


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTH_")

    session_expire_seconds: int = 60 * 60 * 24 * 30 # 30 дней


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    debug: bool = True
    uvicorn: UvicornSettings = UvicornSettings()
    auth: AuthSettings = AuthSettings()
