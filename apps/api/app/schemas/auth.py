"""Pydantic DTOs for the auth router. `extra='forbid'` is enforced everywhere."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.infra.db.models.users import UserRole


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginIn(_StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class LoginOut(_StrictModel):
    id: str
    email: str
    role: UserRole
    display_name: str


class MeOut(LoginOut):
    pass


class PasswordResetRequestIn(_StrictModel):
    email: EmailStr


class PasswordResetConfirmIn(_StrictModel):
    token: str = Field(min_length=10, max_length=512)
    new_password: str = Field(min_length=12, max_length=200)


class AdminCreateUserIn(_StrictModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=200)
    role: UserRole
    display_name: str = Field(min_length=1, max_length=120)
