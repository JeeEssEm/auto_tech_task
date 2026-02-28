import datetime
import uuid

import structlog
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError, InvalidHash

from backend.app.infrastructure.persistent.user import UserRepository
from backend.app.web.schemas.user import SignupUser, LoginUser
from backend.app.web.exceptions import UserAlreadyExists, InvalidCredentials, UserIsNotActivated
from backend.app.infrastructure.config import AppSettings

logger = structlog.get_logger(__name__)


class UserService:
    def __init__(self, user_repo: UserRepository, config: AppSettings):
        self._user_repo = user_repo
        self._ph = PasswordHasher()
        self._settings = config
        self._check_activity = config.auth.user_active

    async def create_user_async(self, user_data: SignupUser):
        pwd_hash = self._ph.hash(user_data.password)

        if await self._user_repo.user_email_exists_async(str(user_data.email)):
            raise UserAlreadyExists(field="email")

        if await self._user_repo.user_login_exists_async(user_data.login):
            raise UserAlreadyExists(field="login")

        user = await self._user_repo.create_user_async(
            login=user_data.login,
            firstname=user_data.firstname,
            middlename=user_data.middlename,
            lastname=user_data.lastname,
            email=str(user_data.email),
            password_hash=pwd_hash
        )
        logger.info("user_created", login=user_data.login, email=str(user_data.email))
        return user

    async def login_user_async(self, user_data: LoginUser, user_agent: str):
        user = await self._user_repo.get_user_by_email_or_login_async(user_data.email_or_login)

        if not user:
            logger.warning("login_failed_user_not_found", identifier=user_data.email_or_login)
            raise InvalidCredentials()

        try:
            if not self._ph.verify(user.password_hash, user_data.password):
                raise InvalidCredentials()
        except (VerificationError, VerifyMismatchError, InvalidHash):
            logger.warning("login_failed_bad_password", user_id=user.id)
            raise InvalidCredentials()

        if self._check_activity and not user.is_active:
            logger.warning("login_failed_not_activated", user_id=user.id)
            raise UserIsNotActivated()

        session_id = str(uuid.uuid4())
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            seconds=self._settings.auth.session_expire_seconds
        )

        await self._user_repo.create_session_async(session_id, user.id, expires_at, user_agent)
        logger.info("user_logged_in", user_id=user.id, user_agent=user_agent)
        return session_id
