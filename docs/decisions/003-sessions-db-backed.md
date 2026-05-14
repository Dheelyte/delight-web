# 003 — Sessions in Postgres, not Redis

- **Status:** accepted
- **Date:** 2026-05-13

## Context

The original prompt stored opaque session tokens in Redis. The addendum removes Redis from the stack to keep Lambda lean and free-tier-friendly. We still need server-side session revocation (so JWTs in localStorage remain off the table).

## Decision

A `sessions` table in Postgres:

- `token_hash` (SHA-256 of the random 32-byte token; the raw token is **never** stored).
- `user_id`, `created_at`, `last_seen_at`, `expires_at`, `ip`, `user_agent`.
- Unique index on `token_hash`; secondary index on `(user_id, expires_at)` for "log out everywhere".
- Expired rows reaped nightly by an EventBridge-triggered Lambda.

Auth throttling lives in an `auth_attempts` table with a sliding-window query, indexed on `(identifier, kind, attempted_at)`. Retention 30 days, trimmed by the same nightly Lambda.

## Consequences

- One extra DB query per authenticated request. Acceptable at blog scale; the query is a single PK lookup on the hash index (<1 ms).
- No Redis dependency anywhere in the stack.
- Token hashing means a DB dump leak does **not** grant session access.
