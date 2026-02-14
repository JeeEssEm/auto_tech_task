from typing import Callable, Awaitable, Any
from functools import wraps

from fastapi import HTTPException
from dishka.integrations.fastapi import inject

from backend.app.domain.user import User
from backend.app.domain.user.value_objects.roles import UserRoles


def permission_required(permission: str):
    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        @inject
        async def wrapper(*args, current_user: User, **kwargs):
            if current_user is None:
                raise HTTPException(status_code=401, detail="Authentication required")
            if not current_user.has_permission(permission):
                raise HTTPException(status_code=403, detail=f"Permission '{permission}' required")
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
