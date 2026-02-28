from typing import AsyncIterable

from taskiq import AsyncBroker
from dishka import Provider, provide, Scope
from prisma import Prisma
import redis.asyncio as aredis

from backend.app.domain.ports import TaskDispatcher
from backend.app.infrastructure.task_dispatcher import TaskiqDispatcher
from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.persistent.user import UserRepository
from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.infrastructure.storage import StorageWorker
from backend.app.services import ChatService

from backend.app.services.user import UserService
from backend.worker.broker import broker


class InfraProvider(Provider):
    def __init__(self, config: AppSettings):
        super().__init__()
        self._config = config

    @provide(scope=Scope.APP)
    def provide_config(self) -> AppSettings:
        return self._config

    @provide(scope=Scope.APP)
    async def get_prisma(self) -> AsyncIterable[Prisma]:
        client = Prisma()
        await client.connect()
        yield client
        await client.disconnect()

    @provide(scope=Scope.SESSION)
    async def get_user_repository(self, db: Prisma) -> UserRepository:
        return UserRepository(db)

    @provide(scope=Scope.SESSION)
    async def get_user_service(self, repo: UserRepository) -> UserService:
        return UserService(repo, self._config)

    @provide(scope=Scope.APP)
    async def provide_s3_storage_worker(self, config: AppSettings) -> AsyncIterable[StorageWorker]:
        storage = StorageWorker(config)
        await storage.start()
        yield storage
        await storage.stop()

    @provide(scope=Scope.SESSION)
    def provide_chat_repository(self, db: Prisma) -> ChatRepository:
        return ChatRepository(db)

    @provide(scope=Scope.SESSION)
    def provide_task_dispatcher(self) -> TaskDispatcher:
        return TaskiqDispatcher()

    @provide(scope=Scope.SESSION)
    def provide_chat_service(self, repo: ChatRepository, storage: StorageWorker, task_dispatcher: TaskDispatcher, config: AppSettings) -> ChatService:
        return ChatService(repo, storage, config, task_dispatcher)

    @provide(scope=Scope.APP)
    def provide_taskiq_broker(self) -> AsyncBroker:
        return broker

    @provide(scope=Scope.APP)
    async def provide_redis_client(self, config: AppSettings) -> AsyncIterable[aredis.Redis]:
        client = aredis.from_url(config.redis.connection_url)
        yield client
        await client.aclose()
