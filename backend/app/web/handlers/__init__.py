from fastapi import FastAPI

from backend.app.web.handlers.user.auth import router as auth_router
from backend.app.web.handlers.user.recovery import router as recovery_router
from backend.app.web.handlers.chat.chat import router as chat_router

routers = [
    auth_router,
    recovery_router,
    chat_router
]


def register_routers(app: FastAPI):
    for router in routers:
        app.include_router(router)
