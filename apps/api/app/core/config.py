"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    secret_key: str = Field(min_length=32)
    database_url: PostgresDsn

    cors_allowed_origins: list[str] = ["http://localhost:3000"]
    # Production must override — `*` is fine for dev but rejected as a security
    # surface in prod by the Host-header middleware (see app.main).
    trusted_hosts: list[str] = ["*"]

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "noreply@localhost"

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
