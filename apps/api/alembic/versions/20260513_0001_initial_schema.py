"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-13
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# asyncpg's prepared-statement protocol forbids multi-statement strings,
# so each item below must be a single SQL statement (the trigger function
# body counts as one - its `$$...$$` quoting keeps it intact).
UPGRADE_STATEMENTS: list[str] = [
    # -- Extensions --
    "CREATE EXTENSION IF NOT EXISTS citext",
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    # -- Enums --
    "CREATE TYPE user_role AS ENUM ('reader', 'editor', 'admin')",
    "CREATE TYPE post_status AS ENUM ('draft', 'scheduled', 'published', 'archived')",
    "CREATE TYPE comment_status AS ENUM ('pending', 'approved', 'spam', 'deleted')",
    "CREATE TYPE subscriber_status AS ENUM ('pending', 'confirmed', 'unsubscribed')",
    "CREATE TYPE auth_attempt_kind AS ENUM ('login', 'reset', 'signup', 'comment', 'subscribe')",
    "CREATE TYPE slug_entity_type AS ENUM ('post', 'tag', 'category', 'series')",
    # -- users --
    """
    CREATE TABLE users (
        id UUID PRIMARY KEY,
        email CITEXT NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role user_role NOT NULL DEFAULT 'reader',
        display_name VARCHAR(120) NOT NULL,
        avatar_url TEXT,
        bio TEXT,
        totp_secret_encrypted TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # -- sessions --
    """
    CREATE TABLE sessions (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash VARCHAR(64) NOT NULL UNIQUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        expires_at TIMESTAMPTZ NOT NULL,
        ip INET,
        user_agent VARCHAR(500)
    )
    """,
    "CREATE INDEX ix_sessions_user_id_expires_at ON sessions(user_id, expires_at)",
    "CREATE INDEX ix_sessions_expires_at ON sessions(expires_at)",
    # -- auth_attempts --
    """
    CREATE TABLE auth_attempts (
        id UUID PRIMARY KEY,
        identifier VARCHAR(255) NOT NULL,
        kind auth_attempt_kind NOT NULL,
        succeeded BOOLEAN NOT NULL,
        attempted_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE INDEX ix_auth_attempts_identifier_kind_attempted_at
        ON auth_attempts(identifier, kind, attempted_at)
    """,
    # -- media --
    """
    CREATE TABLE media (
        id UUID PRIMARY KEY,
        cloudinary_public_id VARCHAR(255) NOT NULL UNIQUE,
        width INTEGER NOT NULL,
        height INTEGER NOT NULL,
        format VARCHAR(16) NOT NULL,
        bytes INTEGER NOT NULL,
        blurhash VARCHAR(128),
        alt VARCHAR(500) NOT NULL DEFAULT '',
        uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # -- taxonomy --
    """
    CREATE TABLE tags (
        id UUID PRIMARY KEY,
        slug VARCHAR(80) NOT NULL UNIQUE,
        name VARCHAR(80) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE categories (
        id UUID PRIMARY KEY,
        slug VARCHAR(80) NOT NULL UNIQUE,
        name VARCHAR(120) NOT NULL,
        description TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE series (
        id UUID PRIMARY KEY,
        slug VARCHAR(80) NOT NULL UNIQUE,
        title VARCHAR(200) NOT NULL,
        description TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # -- posts --
    """
    CREATE TABLE posts (
        id UUID PRIMARY KEY,
        slug VARCHAR(80) NOT NULL UNIQUE,
        title VARCHAR(200) NOT NULL,
        excerpt TEXT,
        content_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        content_html TEXT NOT NULL DEFAULT '',
        cover_image_id UUID REFERENCES media(id) ON DELETE SET NULL,
        author_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        status post_status NOT NULL DEFAULT 'draft',
        published_at TIMESTAMPTZ,
        scheduled_for TIMESTAMPTZ,
        series_id UUID REFERENCES series(id) ON DELETE SET NULL,
        series_order INTEGER,
        category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
        reading_time_minutes INTEGER NOT NULL DEFAULT 1,
        view_count INTEGER NOT NULL DEFAULT 0,
        search_vector TSVECTOR,
        meta_title VARCHAR(70),
        meta_description VARCHAR(200),
        canonical_url VARCHAR(500),
        robots VARCHAR(80),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_posts_series_id_order_both_or_neither CHECK (
            (series_id IS NULL AND series_order IS NULL)
            OR (series_id IS NOT NULL AND series_order IS NOT NULL)
        ),
        CONSTRAINT uq_post_series_order UNIQUE (series_id, series_order)
    )
    """,
    "CREATE INDEX ix_posts_status_published_at ON posts(status, published_at)",
    "CREATE INDEX ix_posts_published_at_desc ON posts(published_at DESC NULLS LAST)",
    "CREATE INDEX ix_posts_author_id ON posts(author_id)",
    "CREATE INDEX ix_posts_category_id ON posts(category_id)",
    "CREATE INDEX ix_posts_search_vector ON posts USING gin(search_vector)",
    # Search-vector trigger function. The $$-quoted body is one statement.
    """
    CREATE OR REPLACE FUNCTION posts_search_vector_trigger() RETURNS trigger AS $$
    BEGIN
        NEW.search_vector :=
            setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(NEW.excerpt, '')), 'B') ||
            setweight(
                to_tsvector(
                    'english',
                    regexp_replace(coalesce(NEW.content_html, ''), '<[^>]+>', ' ', 'g')
                ),
                'C'
            );
        RETURN NEW;
    END
    $$ LANGUAGE plpgsql
    """,
    """
    CREATE TRIGGER posts_search_vector_update
        BEFORE INSERT OR UPDATE OF title, excerpt, content_html ON posts
        FOR EACH ROW EXECUTE FUNCTION posts_search_vector_trigger()
    """,
    # -- post_tags --
    """
    CREATE TABLE post_tags (
        post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
        PRIMARY KEY (post_id, tag_id)
    )
    """,
    "CREATE INDEX ix_post_tags_tag_id ON post_tags(tag_id)",
    # -- post_revisions --
    """
    CREATE TABLE post_revisions (
        id UUID PRIMARY KEY,
        post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        title VARCHAR(200) NOT NULL,
        content_json JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by UUID REFERENCES users(id) ON DELETE SET NULL,
        is_autosave BOOLEAN NOT NULL DEFAULT TRUE
    )
    """,
    "CREATE INDEX ix_post_revisions_post_id_created_at ON post_revisions(post_id, created_at)",
    # -- comments --
    """
    CREATE TABLE comments (
        id UUID PRIMARY KEY,
        post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        parent_id UUID REFERENCES comments(id) ON DELETE CASCADE,
        author_name VARCHAR(120) NOT NULL,
        author_email_hash VARCHAR(64) NOT NULL,
        content TEXT NOT NULL,
        status comment_status NOT NULL DEFAULT 'pending',
        ip_hash VARCHAR(64) NOT NULL,
        user_agent VARCHAR(500),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX ix_comments_post_id_status_created_at ON comments(post_id, status, created_at)",
    "CREATE INDEX ix_comments_parent_id ON comments(parent_id)",
    # -- subscribers --
    """
    CREATE TABLE subscribers (
        id UUID PRIMARY KEY,
        email CITEXT NOT NULL UNIQUE,
        status subscriber_status NOT NULL DEFAULT 'pending',
        confirmation_token_hash VARCHAR(64),
        unsubscribe_token_hash VARCHAR(64) NOT NULL,
        confirmed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        ip INET
    )
    """,
    # -- page_views (partitioned by month) --
    """
    CREATE TABLE page_views (
        id UUID NOT NULL,
        post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
        session_hash VARCHAR(64) NOT NULL,
        country_code VARCHAR(2),
        referrer_host VARCHAR(255),
        viewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT pk_page_views PRIMARY KEY (id, viewed_at)
    ) PARTITION BY RANGE (viewed_at)
    """,
    "CREATE INDEX ix_page_views_post_id_viewed_at ON page_views(post_id, viewed_at)",
    "CREATE INDEX ix_page_views_viewed_at ON page_views(viewed_at)",
    "CREATE TABLE page_views_default PARTITION OF page_views DEFAULT",
    # -- audit_log --
    """
    CREATE TABLE audit_log (
        id UUID PRIMARY KEY,
        actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
        action VARCHAR(80) NOT NULL,
        resource_type VARCHAR(40) NOT NULL,
        resource_id VARCHAR(80),
        metadata JSONB,
        ip INET,
        user_agent VARCHAR(500),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX ix_audit_log_actor_id_created_at ON audit_log(actor_id, created_at)",
    "CREATE INDEX ix_audit_log_resource ON audit_log(resource_type, resource_id)",
    # -- slug_history --
    """
    CREATE TABLE slug_history (
        id UUID PRIMARY KEY,
        entity_type slug_entity_type NOT NULL,
        entity_id UUID NOT NULL,
        old_slug VARCHAR(80) NOT NULL,
        new_slug VARCHAR(80) NOT NULL,
        changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ck_slug_history_old_and_new_differ CHECK (old_slug <> new_slug)
    )
    """,
    "CREATE INDEX ix_slug_history_entity_type_old_slug ON slug_history(entity_type, old_slug)",
    "CREATE INDEX ix_slug_history_entity ON slug_history(entity_type, entity_id)",
    # -- outbox --
    """
    CREATE TABLE outbox (
        id UUID PRIMARY KEY,
        topic VARCHAR(80) NOT NULL,
        payload_json JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        processed_at TIMESTAMPTZ,
        last_error TEXT
    )
    """,
    "CREATE INDEX ix_outbox_unprocessed ON outbox(created_at) WHERE processed_at IS NULL",
]


DOWNGRADE_STATEMENTS: list[str] = [
    "DROP TABLE IF EXISTS outbox CASCADE",
    "DROP TABLE IF EXISTS slug_history CASCADE",
    "DROP TABLE IF EXISTS audit_log CASCADE",
    "DROP TABLE IF EXISTS page_views CASCADE",
    "DROP TABLE IF EXISTS subscribers CASCADE",
    "DROP TABLE IF EXISTS comments CASCADE",
    "DROP TABLE IF EXISTS post_revisions CASCADE",
    "DROP TABLE IF EXISTS post_tags CASCADE",
    "DROP TRIGGER IF EXISTS posts_search_vector_update ON posts",
    "DROP FUNCTION IF EXISTS posts_search_vector_trigger()",
    "DROP TABLE IF EXISTS posts CASCADE",
    "DROP TABLE IF EXISTS series CASCADE",
    "DROP TABLE IF EXISTS categories CASCADE",
    "DROP TABLE IF EXISTS tags CASCADE",
    "DROP TABLE IF EXISTS media CASCADE",
    "DROP TABLE IF EXISTS auth_attempts CASCADE",
    "DROP TABLE IF EXISTS sessions CASCADE",
    "DROP TABLE IF EXISTS users CASCADE",
    "DROP TYPE IF EXISTS slug_entity_type",
    "DROP TYPE IF EXISTS auth_attempt_kind",
    "DROP TYPE IF EXISTS subscriber_status",
    "DROP TYPE IF EXISTS comment_status",
    "DROP TYPE IF EXISTS post_status",
    "DROP TYPE IF EXISTS user_role",
]


def upgrade() -> None:
    for stmt in UPGRADE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in DOWNGRADE_STATEMENTS:
        op.execute(stmt)
