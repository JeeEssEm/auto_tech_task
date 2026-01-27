from typing import AsyncIterable

from dishka import Provider, provide, Scope
from prisma import Prisma

from ..config import AppSettings

from ..persistent.user import UserRepository
from backend.app.services.user import UserService


class AppProvider(Provider):
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
