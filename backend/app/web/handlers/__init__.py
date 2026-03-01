from fastapi import FastAPI

from backend.app.web.handlers.user.auth import router as auth_router
from backend.app.web.handlers.user.recovery import router as recovery_router
from backend.app.web.handlers.user.profile import router as profile_router
from backend.app.web.handlers.chat.chat import router as chat_router
from backend.app.web.handlers.chat.ws import router as chat_websocket_router

routers = [
    auth_router,
    recovery_router,
    profile_router,
    chat_router,
    chat_websocket_router
]


def register_routers(app: FastAPI):
    for router in routers:
        app.include_router(router)
