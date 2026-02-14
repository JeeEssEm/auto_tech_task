from dataclasses import dataclass

from backend.app.domain.user.value_objects.roles import UserRoles


@dataclass(frozen=True)
class User:
    id: int

    email: str
    login: str

    firstname: str
    middlename: str
    lastname: str

    role: UserRoles
    permissions: set[str]

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def has_role_at_least(self, role: UserRoles) -> bool:
        return self.role.value >= role.value
