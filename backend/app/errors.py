from typing import Any

from fastapi import HTTPException


class ApiError(HTTPException):
    """HTTP error with a stable machine-readable ``code`` in the response body.

    Response shape: ``{"detail": {"code": ..., "message": ..., **extra}}``.
    """

    def __init__(self, status_code: int, code: str, message: str, **extra: Any) -> None:
        detail: dict[str, Any] = {"code": code, "message": message}
        detail.update(extra)
        super().__init__(status_code=status_code, detail=detail)
        self.code = code
