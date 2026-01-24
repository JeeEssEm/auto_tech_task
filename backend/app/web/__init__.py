from fastapi import FastAPI


routers = []


def register_routers(app: FastAPI):
    for router in routers:
        app.include_router(router)
