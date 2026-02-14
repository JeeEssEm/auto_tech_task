from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from .general import validation_exception_handler, base_web_exception_handler
from backend.app.web.exceptions.base_exception import BaseWebException

exception_handlers = [
    (validation_exception_handler, RequestValidationError),
    (base_web_exception_handler, BaseWebException)
]


def register_exception_handlers(app: FastAPI):
    for handler, exc in exception_handlers:
        app.add_exception_handler(exc, handler)
