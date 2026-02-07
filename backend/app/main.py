import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from taskiq import AsyncBroker

from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.di import setup_di
from backend.app.web.handlers import register_routers

from backend.worker import register_tasks


def create_lifespan(config: AppSettings):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container = app.state.dishka_container
        broker: AsyncBroker = await container.get(AsyncBroker)

        register_tasks(broker)
        await broker.startup()

        yield

        await broker.shutdown()

    return lifespan


def create_app(config: AppSettings):
    app = FastAPI(title="Auto technical task generator API", lifespan=create_lifespan(config))
    # TODO: CORS

    register_routers(app)
    setup_di(app, config)

    @app.get("/health")
    async def check_health():
        return True

    return app


async def main():
    config = AppSettings()

    app = create_app(config)

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=config.uvicorn.host,
            port=config.uvicorn.port,
            workers=config.uvicorn.workers,
        )
    )
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
