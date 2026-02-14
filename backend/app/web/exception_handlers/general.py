from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from backend.app.web.exceptions.base_exception import BaseWebException


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error = exc.errors()[0]

    field_name = error.get("loc")[-1] if error.get("loc") else "unknown"

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": error.get("msg"),
                "details": {
                    "field": str(field_name),
                    "type": error.get("type")
                }
            }
        },
    )


async def base_web_exception_handler(request: Request, exc: BaseWebException):
    content = {
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.detail or {}
            }
        }

    if exc.field:
        content["error"]["details"]["field"] = exc.field

    return JSONResponse(
        status_code=exc.http_code,
        content=content
    )
