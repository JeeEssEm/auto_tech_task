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

    PASSWORD: str | None = None
    USER: str = "default"
    USER_PASSWORD: str | None = None
    USE_ACL: bool = False
    HOST: str = "localhost"
    PORT: int = 6379

    @property
    def connection_url(self) -> str:
        password = self.PASSWORD or self.USER_PASSWORD
        if not password:
            return f"redis://{self.HOST}:{self.PORT}"

        if self.USE_ACL:
            return f"redis://{self.USER}:{password}@{self.HOST}:{self.PORT}"

        return f"redis://:{password}@{self.HOST}:{self.PORT}"


class RabbitMqSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RABBITMQ_")

    DEFAULT_USER: str
    DEFAULT_PASS: str

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

    ACCESS_KEY: str
    SECRET_KEY: str

    REGION: str = ""
    BUCKET_NAME: str = "user-files"

    @property
    def connection_url(self) -> str:
        return f"http://{self.HOST}:{self.PORT}"


class QuotaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QUOTA_")

    free_daily_messages: int = 10
    free_daily_uploads: int = 5
    free_max_chats: int = 3

    pro_daily_messages: int = 100
    pro_daily_uploads: int = 50
    pro_max_chats: int = -1  # -1 = unlimited


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]
    uvicorn: UvicornSettings = UvicornSettings()
    auth: AuthSettings = AuthSettings()
    rabbitmq: RabbitMqSettings = RabbitMqSettings()
    redis: RedisSettings = RedisSettings()
    task_queue: TaskQueueSettings = TaskQueueSettings()
    storage: StorageSettings = StorageSettings()
    quota: QuotaSettings = QuotaSettings()
