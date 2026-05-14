"""User model. Roles drive authorisation (see app.core.security in Stage 2)."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String, Text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.db.base import Base, TimestampsMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.infra.db.models.content import Post


class UserRole(str, enum.Enum):
    reader = "reader"
    editor = "editor"
    admin = "admin"


class User(UUIDPKMixin, TimestampsMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True, validate_strings=True),
        nullable=False,
        default=UserRole.reader,
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # Fernet-encrypted; stored as text. Decryption key is derived from SECRET_KEY.
    totp_secret_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)

    posts: Mapped[list[Post]] = relationship(
        "Post", back_populates="author", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"
