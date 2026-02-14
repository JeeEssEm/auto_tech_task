class BaseWebException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        http_code: int,
        field: str | None = None,
        detail: dict | None = None
    ):
        self.code = code
        self.message = message
        self.field = field
        self.http_code = http_code
        self.detail = detail
        super().__init__(message)
