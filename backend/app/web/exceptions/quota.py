from fastapi import status

from backend.app.web.exceptions.base_exception import BaseWebException


class QuotaExceeded(BaseWebException):
    def __init__(self, action: str, limit: int):
        super().__init__(
            code="QUOTA_EXCEEDED",
            message=f"Daily quota for `{action}` exceeded (limit: {limit})",
            detail={"action": action, "limit": limit},
            http_code=status.HTTP_429_TOO_MANY_REQUESTS
        )
