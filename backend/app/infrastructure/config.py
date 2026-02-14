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
    user_active: bool = False


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    PASSWORD: str = "chage_me_in_prod"
    USER: str = "some_user"
    USER_PASSWORD: str = "naaah_change_me"
    HOST: str = "localhost"
    PORT: int = 6379

    @property
    def connection_url(self) -> str:
        return f"redis://{self.USER}:{self.USER_PASSWORD}@{self.HOST}:{self.PORT}"


class RabbitMqSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RABBITMQ_")

    DEFAULT_USER: str = "non_default_user"
    DEFAULT_PASS: str = "non_default_pass"

    HOST: str = "localhost"
    PORT: int = 5672

    @property
    def connection_url(self) -> str:
        return f"amqp://{self.DEFAULT_USER}:{self.DEFAULT_PASS}@{self.HOST}:{self.PORT}/"


class TaskQueueSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TASK_QUEUE_")
    queue_name: str = "tasks"


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STORAGE_")

    HOST: str = "localhost"
    PORT: int = 8333

    ACCESS_KEY: str = "change-me-in-prod"
    SECRET_KEY: str = "definitely-change-me-in-prod"

    REGION: str = ""
    BUCKET_NAME: str = "user-files"

    @property
    def connection_url(self) -> str:
        return f"http://{self.HOST}:{self.PORT}"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    debug: bool = True
    uvicorn: UvicornSettings = UvicornSettings()
    auth: AuthSettings = AuthSettings()
    rabbitmq: RabbitMqSettings = RabbitMqSettings()
    redis: RedisSettings = RedisSettings()
    task_queue: TaskQueueSettings = TaskQueueSettings()
    storage: StorageSettings = StorageSettings()
