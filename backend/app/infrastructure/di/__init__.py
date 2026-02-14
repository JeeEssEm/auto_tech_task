from dishka.integrations.fastapi import setup_dishka
from dishka import make_async_container
from fastapi import FastAPI

from backend.app.infrastructure.di.infra_provider import InfraProvider
from backend.app.infrastructure.di.auth_provider import AuthProvider

from backend.app.infrastructure.config import AppSettings


def setup_di(app: FastAPI, config: AppSettings):
    container = make_async_container(InfraProvider(config), AuthProvider(config))
    setup_dishka(container=container, app=app)
