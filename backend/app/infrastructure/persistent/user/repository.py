import datetime

from prisma import Prisma
from prisma.models import User
from prisma.types import (
    UserCreateInput, UserWhereInput, UserWhereInputRecursive1,
    SessionWhereInput, SessionWhereUniqueInput, SessionInclude, SessionCreateInput,
    DateTimeFilter, SubscriptionLogWhereInput, UsageRecordCreateInput, UsageRecordWhereInput
)

from backend.app.domain.user import User as DomainUser
from backend.app.domain.user.value_objects.roles import UserRoles


class UserRepository:
    def __init__(self, db: Prisma):
        self._db = db

    async def create_user_async(
            self, email: str, login: str, firstname: str, middlename: str, lastname: str, password_hash: str
    ) -> User:
        return await self._db.user.create(
            UserCreateInput(
                email=email,
                login=login,
                first_name=firstname,
                middle_name=middlename,
                last_name=lastname,
                password_hash=password_hash,
                role=UserRoles.MEMBER
            )
        )

    async def user_login_exists_async(self, login: str) -> bool:
        return await self._db.user.find_first(where=UserWhereInput(login=login)) is not None

    async def user_email_exists_async(self, email: str) -> bool:
        return await self._db.user.find_first(where=UserWhereInput(email=email)) is not None

    async def get_user_by_email_or_login_async(self, login_or_email: str) -> User | None:
        user = await self._db.user.find_first(
            where=UserWhereInput(
                OR=[
                    UserWhereInputRecursive1(email=login_or_email),
                    UserWhereInputRecursive1(login=login_or_email)
                ]
            )
        )
        return user

    async def get_user_by_session_id_async(self, session_id: str) -> User | None:
        now = datetime.datetime.now(datetime.timezone.utc)
        session = await self._db.session.find_first(
            where=SessionWhereInput(
                id=session_id,
                expires_at=DateTimeFilter(gt=now),
            ),
            include=SessionInclude(user=True)
        )
        if not session:
            return None

        return session.user

    async def create_session_async(self, session_id: str, user_id: int, expires_at: datetime.datetime, user_agent: str):
        await self._db.session.create(
            SessionCreateInput(
                id=session_id,
                user_id=user_id,
                expires_at=expires_at,
                user_agent=user_agent
            )
        )

    async def delete_session_async(self, session_id: str):
        await self._db.session.delete(where=SessionWhereUniqueInput(id=session_id))

    async def get_active_subscription_tier_async(self, user_id: int) -> str | None:
        now = datetime.datetime.now(datetime.timezone.utc)
        sub = await self._db.subscriptionlog.find_first(
            where=SubscriptionLogWhereInput(
                user_id=user_id,
                start_dt=DateTimeFilter(lte=now),
                till_dt=DateTimeFilter(gt=now),
            ),
            order={"till_dt": "desc"},
        )
        return sub.tier if sub else None

    async def record_usage_async(self, user_id: int, action: str) -> None:
        await self._db.usagerecord.create(
            UsageRecordCreateInput(user_id=user_id, action=action)
        )

    async def count_usage_today_async(self, user_id: int, action: str) -> int:
        start_of_day = datetime.datetime.now(datetime.timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return await self._db.usagerecord.count(
            where=UsageRecordWhereInput(
                user_id=user_id,
                action=action,
                created_at=DateTimeFilter(gte=start_of_day),
            )
        )

    async def count_total_chats_async(self, user_id: int) -> int:
        return await self._db.chat.count(where={"owner_id": user_id})

    async def get_today_usage_summary_async(self, user_id: int) -> dict[str, int]:
        start_of_day = datetime.datetime.now(datetime.timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        records = await self._db.usagerecord.find_many(
            where=UsageRecordWhereInput(
                user_id=user_id,
                created_at=DateTimeFilter(gte=start_of_day),
            )
        )
        summary: dict[str, int] = {}
        for r in records:
            summary[r.action] = summary.get(r.action, 0) + 1
        return summary
