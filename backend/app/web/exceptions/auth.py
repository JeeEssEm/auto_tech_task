from fastapi import status

from backend.app.web.exceptions.base_exception import BaseWebException


class UserAlreadyExists(BaseWebException):
    def __init__(self, field: str = "email"):
        super().__init__(
            code="AUTH_USER_ALREADY_EXISTS",
            message="User with this credential already exists",
            field=field,
            http_code=status.HTTP_400_BAD_REQUEST
        )


class UserNotFound(BaseWebException):
    def __init__(self):
        super().__init__(
            code="AUTH_USER_NOT_FOUND",
            message="User with this credential not found",
            http_code=status.HTTP_404_NOT_FOUND
        )


class InvalidCredentials(BaseWebException):
    def __init__(self):
        super().__init__(
            code="AUTH_USER_WRONG_PASSWORD_OR_LOGIN",
            message="User's password or login is incorrect",
            http_code=status.HTTP_400_BAD_REQUEST
        )


class InvalidSession(BaseWebException):
    def __init__(self, field: str = "session_id"):
        super().__init__(
            code="AUTH_USER_SESSION_NOT_FOUND",
            message="User with this `session_id` not found",
            field=field,
            http_code=status.HTTP_401_UNAUTHORIZED
        )


class ExpiredSession(BaseWebException):
    def __init__(self):
        super().__init__(
            code="AUTH_USER_SESSION_EXPIRED",
            message="This `session_id` is expired",
            http_code=status.HTTP_401_UNAUTHORIZED
        )


class UserIsNotActivated(BaseWebException):
    def __init__(self):
        super().__init__(
            code="AUTH_USER_IS_NOT_ACTIVATED",
            message="User account is not activated",
            http_code=status.HTTP_400_BAD_REQUEST
        ) # TODO: добавить обработку на фронт


class AuthRequired(BaseWebException):
    def __init__(self):
        super().__init__(
            code="AUTH_USER_IS_NOT_AUTHENTICATED",
            message="User account is not authenticated",
            http_code=status.HTTP_401_UNAUTHORIZED
        ) # TODO: добавить обработку на фронт


class NotEnoughPermissions(BaseWebException):
    def __init__(self, minimum_role: str):
        super().__init__(
            code="AUTH_NOT_ENOUGH_PERMISSIONS",
            message=f"User role must be at least `{minimum_role}`",
            http_code=status.HTTP_403_FORBIDDEN
        ) # TODO: добавить обработку на фронт
