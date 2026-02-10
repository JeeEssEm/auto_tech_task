from typing import AsyncIterable

from taskiq import AsyncBroker
from dishka import Provider, provide, Scope
from prisma import Prisma

from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.persistent.user import UserRepository
from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.infrastructure.storage import StorageWorker
from backend.app.services import ChatService

from backend.app.services.user import UserService
from backend.worker import create_broker_from_config


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

    @provide(scope=Scope.REQUEST)
    async def get_user_repository(self, db: Prisma) -> UserRepository:
        return UserRepository(db)

    @provide(scope=Scope.REQUEST)
    async def get_user_service(self, repo: UserRepository) -> UserService:
        return UserService(repo, self._config)

    @provide(scope=Scope.APP)
    def provide_taskiq_broker(self) -> AsyncBroker:
        return create_broker_from_config(self._config)

    @provide(scope=Scope.APP)
    def provide_s3_storage_worker(self, config: AppSettings) -> StorageWorker:
        return StorageWorker(config)

    @provide(scope=Scope.REQUEST)
    def provide_chat_repository(self, db: Prisma) -> ChatRepository:
        return ChatRepository(db)

    @provide(scope=Scope.REQUEST)
    def provide_chat_service(self, repo: ChatRepository, storage: StorageWorker, config: AppSettings) -> ChatService:
        return ChatService(repo, storage, config)
