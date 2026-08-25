"""Application error types and the global exception handlers wired in main.py."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

# Starlette renamed this constant between versions; the numeric code is stable.
_HTTP_422 = 422

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for expected, domain-level failures.

    Handlers below turn these into a stable JSON error envelope so the frontend
    never has to guess the shape of a failure.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"
    message: str = "Application error."

    def __init__(self, message: str | None = None, *, details: Any = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "Resource not found."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    message = "Resource already exists."


class ValidationError(AppError):
    status_code = _HTTP_422
    code = "validation_error"
    message = "Invalid input."


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_error"
    message = "Could not validate credentials."


class PermissionError_(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"
    message = "You do not have access to this resource."


def _envelope(code: str, message: str, details: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global handlers so no raw traceback ever reaches a client."""

    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        logger.info(
            "app_error code=%s status=%s message=%s", exc.code, exc.status_code, exc.message
        )
        headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"][1:]) or "body",
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=_HTTP_422,
            content=_envelope("validation_error", "Request validation failed.", details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "authentication_error", 403: "forbidden", 404: "not_found"}.get(
            exc.status_code, "http_error"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("internal_error", "An unexpected error occurred."),
        )
