from dishka.integrations.fastapi import setup_dishka
from dishka import make_async_container
from fastapi import FastAPI

from .providers import AppProvider
from backend.app.infrastructure.config import AppSettings


def setup_di(app: FastAPI, config: AppSettings):
    container = make_async_container(AppProvider(config))
    setup_dishka(container=container, app=app)
