-- Runs once when the Postgres container is first created.
-- The migration also CREATEs these extensions defensively, so any new
-- environment (Neon, RDS) bootstraps cleanly without touching this file.

CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE DATABASE blog_test OWNER blog;

\connect blog_test
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
