import structlog

from backend.app.infrastructure.persistent.user import UserRepository
from backend.app.infrastructure.config import AppSettings
from backend.app.domain.chat.value_objects.types import SubscriptionTier, UsageAction
from backend.app.web.exceptions import QuotaExceeded

logger = structlog.get_logger(__name__)


_UNLIMITED = -1 # без ограничений


class QuotaService:
    def __init__(self, user_repo: UserRepository, config: AppSettings):
        self._user_repo = user_repo
        self._limits = self._build_limits(config)

    @staticmethod
    def _build_limits(config: AppSettings) -> dict[SubscriptionTier, dict[UsageAction, int]]:
        q = config.quota
        return {
            SubscriptionTier.FREE: {
                UsageAction.GENERATE_TZ: q.free_daily_messages,
                UsageAction.PARSE_FILE: q.free_daily_uploads,
                UsageAction.CREATE_CHAT: q.free_max_chats,
            },
            SubscriptionTier.PRO: {
                UsageAction.GENERATE_TZ: q.pro_daily_messages,
                UsageAction.PARSE_FILE: q.pro_daily_uploads,
                UsageAction.CREATE_CHAT: q.pro_max_chats,
            },
            SubscriptionTier.ENTERPRISE: {
                UsageAction.GENERATE_TZ: _UNLIMITED,
                UsageAction.PARSE_FILE: _UNLIMITED,
                UsageAction.CREATE_CHAT: _UNLIMITED,
            },
        }

    async def get_user_tier_async(self, user_id: int) -> SubscriptionTier:
        tier_str = await self._user_repo.get_active_subscription_tier_async(user_id)
        if tier_str is None:
            return SubscriptionTier.FREE
        try:
            return SubscriptionTier(tier_str)
        except ValueError:
            return SubscriptionTier.FREE

    async def check_and_record_async(self, user_id: int, action: UsageAction) -> None:
        tier = await self.get_user_tier_async(user_id)
        limit = self._limits.get(tier, {}).get(action, 0)

        if limit == _UNLIMITED:
            await self._user_repo.record_usage_async(user_id, action)
            return

        if action == UsageAction.CREATE_CHAT:
            current = await self._user_repo.count_total_chats_async(user_id)
        else:
            current = await self._user_repo.count_usage_today_async(user_id, action)

        if current >= limit:
            logger.warning(
                "quota_exceeded",
                user_id=user_id,
                action=action,
                tier=tier,
                current=current,
                limit=limit,
            )
            raise QuotaExceeded(action=action, limit=limit)

        await self._user_repo.record_usage_async(user_id, action)

    async def get_usage_summary_async(self, user_id: int) -> dict:
        tier = await self.get_user_tier_async(user_id)
        today = await self._user_repo.get_today_usage_summary_async(user_id)
        total_chats = await self._user_repo.count_total_chats_async(user_id)
        limits = self._limits.get(tier, {})

        return {
            "tier": tier,
            "today": {
                UsageAction.GENERATE_TZ: today.get(UsageAction.GENERATE_TZ, 0),
                UsageAction.PARSE_FILE: today.get(UsageAction.PARSE_FILE, 0),
            },
            "total_chats": total_chats,
            "limits": {action: lim for action, lim in limits.items()},
        }
