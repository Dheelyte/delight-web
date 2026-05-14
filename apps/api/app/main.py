"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from mangum import Mangum

from sqlalchemy import select

from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger


from app.core.db import session_scope
from app.core.security import hash_password
from app.infra.db.models.users import User, UserRole


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    get_logger(__name__).info("api.startup", environment=get_settings().ENVIRONMENT)

    email = get_settings().DEFAULT_ADMIN_EMAIL
    password = get_settings().DEFAULT_ADMIN_PASSWORD
    async with session_scope() as session:
        existing = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        admin = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.admin,
            display_name="Admin",
            bio="Default admin account",
        )
        session.add(admin)
        await session.commit()
    yield


# Response headers applied to every API response. The web proxy strips any of
# these that conflict with what Next sets, so the two layers are independent.
_SECURITY_HEADERS: dict[str, str] = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
}


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Delight Web API",
        version="0.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    # Reject requests with an unexpected Host header - first line of defence
    # against host-header injection attacks in production.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for k, v in _SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if settings.is_production:
            response.headers.setdefault(
                "strict-transport-security",
                "max-age=31536000; includeSubDomains; preload",
            )
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    app.include_router(v1_router, prefix="/api")

    return app


app = create_app()

handler = Mangum(app)
