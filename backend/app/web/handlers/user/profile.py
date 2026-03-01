from fastapi import APIRouter

from dishka.integrations.fastapi import FromDishka, DishkaRoute

from backend.app.infrastructure.auth.typed_roles import AuthenticatedUser
from backend.app.services.quota import QuotaService
from backend.app.domain.chat.value_objects.types import UsageAction
from backend.app.web.schemas.user.profile import UserProfile, UsageStats, TodayUsage, UsageLimits

router = APIRouter(prefix="/auth", route_class=DishkaRoute, tags=["auth", "profile"])


@router.get("/me")
async def get_profile(
        user: FromDishka[AuthenticatedUser],
        quota_service: FromDishka[QuotaService],
) -> UserProfile:
    tier = await quota_service.get_user_tier_async(user.id)

    return UserProfile(
        id=user.id,
        email=user.email,
        login=user.login,
        firstname=user.firstname,
        middlename=user.middlename,
        lastname=user.lastname,
        role=str(user.role),
        is_active=True,
        subscription_tier=tier,
    )


@router.get("/me/usage")
async def get_usage(
        user: FromDishka[AuthenticatedUser],
        quota_service: FromDishka[QuotaService],
) -> UsageStats:
    summary = await quota_service.get_usage_summary_async(user.id)
    limits = summary["limits"]

    return UsageStats(
        tier=summary["tier"],
        today=TodayUsage(
            generate_tz=summary["today"].get(UsageAction.GENERATE_TZ, 0),
            parse_file=summary["today"].get(UsageAction.PARSE_FILE, 0),
        ),
        total_chats=summary["total_chats"],
        limits=UsageLimits(
            generate_tz=limits.get(UsageAction.GENERATE_TZ, 0),
            parse_file=limits.get(UsageAction.PARSE_FILE, 0),
            create_chat=limits.get(UsageAction.CREATE_CHAT, 0),
        ),
    )
