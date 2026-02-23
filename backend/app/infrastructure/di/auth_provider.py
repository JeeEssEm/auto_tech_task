from dishka import Provider, provide, Scope, from_context
from fastapi import Request

from backend.app.domain.user.entities import User
from backend.app.domain.user.value_objects.roles import UserRoles
from backend.app.infrastructure.auth.typed_roles import AuthenticatedUser, StaffUser, SuperUser

from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.persistent.user import UserRepository

from backend.app.web.exceptions import AuthRequired, NotEnoughPermissions, UserIsNotActivated


class AuthProvider(Provider):
    request = from_context(provides=Request, scope=Scope.REQUEST)

    def __init__(self, config: AppSettings):
        super().__init__()
        self._check_activated = config.auth.user_active

    @provide(scope=Scope.REQUEST)
    async def get_optional_user(
            self, request: Request, repo: UserRepository
    ) -> User | None:
        session_id = request.cookies.get("session_id")

        if not session_id:
            return None

        user = await repo.get_user_by_session_id_async(session_id)
        if not user:
            await repo.delete_session_async(session_id)
            return None

        if self._check_activated and not user.is_active:
            raise UserIsNotActivated()

        return User(
            id=user.id,
            email=user.email,
            login=user.login,
            firstname=user.first_name,
            middlename=user.middle_name,
            lastname=user.last_name,
            role=UserRoles(user.role),
            permissions=set()  # TODO: исправить, если появятся permissions
        )

    @provide(scope=Scope.REQUEST)
    async def get_authenticated_user(self, user: User | None) -> AuthenticatedUser:
        if user is None:
            raise AuthRequired()
        return AuthenticatedUser(user)

    @provide(scope=Scope.REQUEST)
    async def get_staff_user(self, user: AuthenticatedUser) -> StaffUser:
        if not user.has_role_at_least(UserRoles.STAFF):
            raise NotEnoughPermissions("Staff")
        return StaffUser(user)

    @provide(scope=Scope.REQUEST)
    async def get_superuser(self, user: AuthenticatedUser) -> SuperUser:
        if not user.has_role_at_least(UserRoles.SUPERUSER):
            raise NotEnoughPermissions("Superuser")
        return SuperUser(user)
