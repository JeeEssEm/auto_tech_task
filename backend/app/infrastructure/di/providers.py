from dishka import Provider, provide, Scope

from ..config import AppSettings


class AppProvider(Provider):
    def __init__(self, config: AppSettings):
        super().__init__()
        self._config = config

    @provide(scope=Scope.APP)
    def provide_config(self) -> AppSettings:
        return self._config
