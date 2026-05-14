"""Auth router.

State transitions are explicit endpoints; nothing here PATCHes a flag.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    SESSION_COOKIE,
    client_ip,
    current_user,
    get_db,
    require_admin,
    user_agent,
)
from app.core.config import get_settings
from app.infra.db.models.users import User
from app.schemas.auth import (
    AdminCreateUserIn,
    LoginIn,
    LoginOut,
    MeOut,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
)
from app.services import auth as auth_service, sessions as sessions_service
from app.services.sessions import SESSION_TTL

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str, ttl: timedelta) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=int(ttl.total_seconds()),
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")


def _user_out(user: User) -> LoginOut:
    return LoginOut(
        id=str(user.id),
        email=user.email,
        role=user.role,
        display_name=user.display_name,
    )


# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginOut)
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginOut:
    token, _row = await auth_service.login(
        db,
        email=body.email,
        password=body.password,
        ip=client_ip(request),
        user_agent=user_agent(request),
    )
    _set_session_cookie(response, token, SESSION_TTL)

    # The user is loaded inside the service but not returned; fetch fresh.
    user = await auth_service.get_user_by_email(db, body.email)
    return _user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if session_token:
        # Prefer the user-id resolved from the session itself for audit trace.
        row = await sessions_service.load_session(db, session_token)
        await auth_service.logout(
            db,
            token=session_token,
            actor_id=row.user_id if row else None,
            ip=client_ip(request),
            user_agent=user_agent(request),
        )
    _clear_session_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await auth_service.logout_all(
        db, user_id=user.id, ip=client_ip(request), user_agent=user_agent(request)
    )
    _clear_session_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(current_user)) -> MeOut:
    return MeOut(**_user_out(user).model_dump())


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


@router.post("/password/reset-request", status_code=status.HTTP_204_NO_CONTENT)
async def password_reset_request(
    body: PasswordResetRequestIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    # Token (if produced) is enqueued via the outbox in Stage 6; for now
    # it's only audit-logged. The HTTP response is identical regardless.
    await auth_service.request_password_reset(
        db,
        email=body.email,
        ip=client_ip(request),
        user_agent=user_agent(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password/reset-confirm", status_code=status.HTTP_204_NO_CONTENT)
async def password_reset_confirm(
    body: PasswordResetConfirmIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    await auth_service.confirm_password_reset(
        db,
        signed_token=body.token,
        new_password=body.new_password,
        ip=client_ip(request),
        user_agent=user_agent(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Admin invite (user creation)
# ---------------------------------------------------------------------------


@router.post("/users", response_model=LoginOut, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    body: AdminCreateUserIn,
    request: Request,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> LoginOut:
    user = await auth_service.admin_create_user(
        db,
        actor=actor,
        email=body.email,
        password=body.password,
        role=body.role,
        display_name=body.display_name,
        ip=client_ip(request),
        user_agent=user_agent(request),
    )
    return _user_out(user)
