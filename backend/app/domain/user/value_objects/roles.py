import enum


class UserRoles(enum.IntEnum):
    # Чем выше значение, тем "старше" роль
    MEMBER = 10
    STAFF = 20
    SUPERUSER = 30

    def __str__(self):
        return self.name.lower()
