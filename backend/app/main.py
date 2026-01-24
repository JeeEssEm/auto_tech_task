import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from infrastructure.config import AppSettings
from infrastructure.di import setup_di


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


async def create_app(config: AppSettings):
    app = FastAPI(title="Auto technical task generator API", lifespan=lifespan)
    # TODO: CORS

    setup_di(app, config)

    @app.get("/health")
    async def check_health():
        return True

    return app


async def main():
    config = AppSettings()

    app = await create_app(config)

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
