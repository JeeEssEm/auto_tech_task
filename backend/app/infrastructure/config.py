import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class UvicornSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="UVICORN_")

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = os.cpu_count()


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTH_")

    jwt_secret: str = "change_me_in_production"
    jwt_algorithm: str = "HS256"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    uvicorn: UvicornSettings = UvicornSettings()
    auth: AuthSettings = AuthSettings()
