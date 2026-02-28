import datetime

from prisma import Prisma
from prisma.models import User
from prisma.types import (
    UserCreateInput, UserWhereInput, UserWhereInputRecursive1,
    SessionWhereInput, SessionWhereUniqueInput, SessionInclude, SessionCreateInput,
    DateTimeFilter
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
