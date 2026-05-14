# api

FastAPI backend for Delight Web. Async SQLAlchemy 2 + Pydantic v2. Packaged for AWS Lambda in production (see `infra/`).

## Dev

```bash
uv sync
cp ../../.env.example ../../.env  # fill values
uv run uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs.

## Scripts

- `uv run pytest` - tests
- `uv run ruff check .` / `uv run ruff format .` - lint/format
- `uv run mypy app` - strict type check
- `uv run alembic upgrade head` - apply migrations
- `uv run alembic downgrade base` - drop everything (dev only)
- `uv run alembic revision --autogenerate -m "msg"` - new migration
- `uv run python -m scripts.seed` - idempotent seed (admin, tags, series, posts)

## Schema

Initial migration `alembic/versions/20260513_0001_initial_schema.py` provisions:

- enums (`user_role`, `post_status`, `comment_status`, `subscriber_status`, `auth_attempt_kind`, `slug_entity_type`)
- core tables: users, sessions, auth_attempts, media, tags, categories, series, posts, post_tags, post_revisions, comments, subscribers, audit_log, slug_history, outbox
- `page_views` partitioned by month on `viewed_at` (default partition only - beat job adds month partitions ahead of time in Stage 6)
- `posts.search_vector` TSVECTOR maintained by trigger (weighted A=title, B=excerpt, C=stripped content_html), GIN-indexed

Slug changes on `posts`, `tags`, `categories`, `series` are captured by an ORM `before_flush` listener (`app/infra/db/events.py`) and written to `slug_history` for 301 redirects.
