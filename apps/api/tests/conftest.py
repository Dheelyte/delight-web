from __future__ import annotations

import os

# Tests must NEVER hit the dev DB — force-set the env before any app import.
# `setdefault` is wrong here: a stray DATABASE_URL in .env would silently win.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://blog:blog@localhost:5432/blog_test",
)
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("SECRET_KEY", "test-secret-key-please-change-min-32-chars")


# --- Shared DB fixtures ----------------------------------------------------
# Defined here (not in tests/_db.py) so pytest auto-discovers them across
# every test file. The `_migrated_db` fixture is the dependency of `db_session`,
# so it must be in the same fixture namespace.

from collections.abc import AsyncIterator, Iterator  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.util.exc import CommandError  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _alembic_config() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    return cfg


@pytest.fixture(scope="session")
def _migrated_db() -> Iterator[None]:
    """Run upgrade head, yield, then downgrade base.

    Skips the integration suite if Postgres is unreachable.
    """
    cfg = _alembic_config()
    try:
        command.upgrade(cfg, "head")
    except (OperationalError, CommandError) as exc:
        pytest.skip(f"Postgres unavailable for integration tests: {exc}")
    try:
        yield
    finally:
        command.downgrade(cfg, "base")


@pytest_asyncio.fixture()
async def db_session(_migrated_db: None) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()
