from fastapi import APIRouter, Request, Response

from dishka.integrations.fastapi import FromDishka, DishkaRoute

from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.persistent.user import UserRepository
from backend.app.web.schemas.user import auth as auth_schemas
from backend.app.services.user import UserService
from backend.app.web.exceptions import InvalidSession

router = APIRouter(prefix="/auth", route_class=DishkaRoute, tags=["auth"])


@router.post("/signup")
async def signup(data: auth_schemas.SignupUser, service: FromDishka[UserService], config: FromDishka[AppSettings]):
    await service.create_user_async(data)
    return auth_schemas.SuccessSignup(
        success=True,
        message=None,
        need_to_activate=config.auth.user_active
    )


@router.post("/login")
async def login(
        data: auth_schemas.LoginUser,
        service: FromDishka[UserService],
        cfg: FromDishka[AppSettings],
        req: Request,
        resp: Response
):
    session_id = await service.login_user_async(data, req.headers.get("User-Agent"))

    resp.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=not cfg.debug,
        max_age=cfg.auth.session_expire_seconds
    )
    # TODO: CSRF protection
    return {
        "message": "ok"
    }


@router.post("/logout")
async def logout(repo: FromDishka[UserRepository], req: Request, resp: Response):
    session_id = req.cookies.get("session_id")
    if session_id is None:
        raise InvalidSession()

    await repo.delete_session_async(session_id)
    resp.delete_cookie("session_id")

    return {
        "message": "ok"
    }


@router.get("/activate")
async def activate_account():
    return


@router.get("/resend-activation-letter")
async def resend_activation_letter():
    return
