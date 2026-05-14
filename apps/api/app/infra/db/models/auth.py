"""Session and auth-attempt tables. See ADR 003."""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import INET, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base, UUIDPKMixin


class Session(UUIDPKMixin, Base):
    __tablename__ = "sessions"

    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # SHA-256 hex of the random token. Raw token is never stored.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip: Mapped[str | None] = mapped_column(INET(), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_sessions_user_id_expires_at", "user_id", "expires_at"),
        Index("ix_sessions_expires_at", "expires_at"),
    )


class AuthAttemptKind(str, enum.Enum):
    login = "login"
    reset = "reset"
    signup = "signup"
    comment = "comment"
    subscribe = "subscribe"


class AuthAttempt(UUIDPKMixin, Base):
    __tablename__ = "auth_attempts"

    # Either an email or an IP, depending on the limit we want to enforce.
    identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[AuthAttemptKind] = mapped_column(
        Enum(AuthAttemptKind, name="auth_attempt_kind", native_enum=True),
        nullable=False,
    )
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "ix_auth_attempts_identifier_kind_attempted_at",
            "identifier",
            "kind",
            "attempted_at",
        ),
    )
