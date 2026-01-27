import datetime
import uuid

from argon2 import PasswordHasher

from backend.app.infrastructure.persistent.user import UserRepository
from backend.app.web.schemas.user import SignupUser, LoginUser
from backend.app.domain.user.exceptions import UserAlreadyExists, UserNotFound, InvalidCredentials
from backend.app.infrastructure.config import AppSettings


class UserService:
    def __init__(self, user_repo: UserRepository, config: AppSettings):
        self._user_repo = user_repo
        self._ph = PasswordHasher()
        self._settings = config

    async def create_user_async(self, user_data: SignupUser):
        pwd_hash = self._ph.hash(user_data.password)

        if not await self._user_repo.user_exists_async(user_data.login, str(user_data.email)):
            return await self._user_repo.create_user_async(user_data.to_domain(), pwd_hash)

        raise UserAlreadyExists()

    async def login_user_async(self, user_data: LoginUser, user_agent: str):
        user = await self._user_repo.get_user_by_email_or_login_async(user_data.email_or_login)

        if not user:
            raise UserNotFound()

        if not self._ph.verify(user.password_hash, user_data.password):
            raise InvalidCredentials()

        session_id = str(uuid.uuid4())
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            seconds=self._settings.auth.session_expire_seconds
        )

        await self._user_repo.create_session_async(session_id, user.id, expires_at, user_agent)
        return session_id
