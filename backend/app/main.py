import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.logging import setup_logging
from backend.app.infrastructure.storage import StorageWorker
from backend.app.infrastructure.di import setup_di
from backend.app.web.handlers import register_routers
from backend.app.web.exception_handlers import register_exception_handlers

from backend.worker.broker import broker


def setup_cors(app: FastAPI, config: AppSettings):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_lifespan(config: AppSettings):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container = app.state.dishka_container

        storage_worker: StorageWorker = await container.get(StorageWorker)
        await storage_worker.create_bucket(config.storage.BUCKET_NAME)

        await broker.startup()

        yield

        await broker.shutdown()

    return lifespan


def create_app(config: AppSettings):
    app = FastAPI(title="Auto technical task generator API", lifespan=create_lifespan(config))

    setup_cors(app, config)
    register_routers(app)
    register_exception_handlers(app)
    setup_di(app, config)

    @app.get("/health")
    async def check_health():
        return True

    return app


async def main():
    config = AppSettings()
    setup_logging(debug=config.debug)

    app = create_app(config)

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=config.uvicorn.host,
            port=config.uvicorn.port,
        )
    )
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
