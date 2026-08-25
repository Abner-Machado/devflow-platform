"""FastAPI application factory and entrypoint."""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.schemas.common import ErrorResponse

logger = get_logger(__name__)

DESCRIPTION = """
DevFlow tracks projects, tasks, technical documentation, activity and delivery
metrics for software teams.

All endpoints below `/api/v1` except `/auth/register` and `/auth/login` require a
bearer access token obtained from the authentication endpoints.
"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info(
        "starting %s env=%s database=%s",
        settings.PROJECT_NAME,
        settings.ENVIRONMENT,
        "sqlite" if settings.is_sqlite else "postgresql",
    )
    if settings.SEED_ON_STARTUP:
        from app.db.seed import seed_database

        seed_database()
    yield
    logger.info("shutting down %s", settings.PROJECT_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        responses={
            400: {"model": ErrorResponse},
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "%s %s -> %s in %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.1f}"
        return response

    @app.get("/health", tags=["system"], summary="Liveness probe")
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app


app = create_app()
