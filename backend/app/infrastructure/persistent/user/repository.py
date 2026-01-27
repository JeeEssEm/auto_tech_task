import datetime

from prisma import Prisma
from prisma.models import User
from prisma.types import (
    UserCreateInput, UserWhereInput, UserWhereInputRecursive1,
    SessionWhereInput, SessionWhereUniqueInput, SessionInclude, SessionCreateInput
)

from backend.app.domain.user import User as DomainUser


class UserRepository:
    def __init__(self, db: Prisma):
        self._db = db

    async def create_user_async(self, user_data: DomainUser, password_hash: str) -> User:
        return await self._db.user.create(
            UserCreateInput(
                email=user_data.email,
                login=user_data.login,
                first_name=user_data.firstname,
                middle_name=user_data.middlename,
                last_name=user_data.lastname,
                password_hash=password_hash
            )
        )

    async def user_exists_async(self, login: str, email: str) -> bool:
        user_count = await self._db.user.count(
            where=UserWhereInput(
                OR=[
                    UserWhereInputRecursive1(email=email),
                    UserWhereInputRecursive1(login=login)
                ]
            )
        )
        return user_count != 0

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
        session = await self._db.session.find_first(
            where=SessionWhereInput(id=session_id),
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
