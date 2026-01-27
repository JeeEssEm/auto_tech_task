from fastapi import APIRouter
from prisma import Prisma

from dishka.integrations.fastapi import FromDishka, DishkaRoute

router = APIRouter(prefix="/recovery", route_class=DishkaRoute, tags=["recovery"])


@router.post("/change-password")
async def change_password(db: FromDishka[Prisma]):
    return await db.user.count()


@router.post("/recover-account")
async def recover_account(db: FromDishka[Prisma]):
    return await db.user.count()

