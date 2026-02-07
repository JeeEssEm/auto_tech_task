from fastapi import APIRouter
from prisma import Prisma

from taskiq import AsyncBroker

from dishka.integrations.fastapi import FromDishka, DishkaRoute

from backend.worker.example.heavy_task import heavy_task

router = APIRouter(prefix="/recovery", route_class=DishkaRoute, tags=["recovery"])


@router.post("/change-password")
async def change_password(db: FromDishka[Prisma]):
    return await db.user.count()


@router.post("/recover-account")
async def recover_account(db: FromDishka[Prisma]):
    return await db.user.count()


@router.post("/heavy-task")
async def post_heavy_task(broker: FromDishka[AsyncBroker]):
    await broker.find_task("heavy_task").kiq(10)

    return "ok"
