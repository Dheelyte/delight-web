# 001 - Monorepo with pnpm workspaces + uv

- **Status:** accepted
- **Date:** 2026-05-13

## Context

We ship two deployable apps (Next.js web, FastAPI api) that share types (generated from the API's OpenAPI schema) and a single deployment lifecycle. We need fast installs, deterministic lockfiles for both ecosystems, and the option to add small shared packages without ceremony.

## Decision

One repo, two ecosystems:

- **Node:** pnpm workspaces; root `package.json` exposes top-level scripts; each app has its own `package.json`. `pnpm-lock.yaml` is committed.
- **Python:** `uv` per Python app (currently only `apps/api`). `uv.lock` is committed.

We deliberately do **not** use Turborepo, Nx, or a polyrepo. A blog this size doesn't need pipeline caching infra, and polyrepo adds cross-PR coordination cost we don't want.

Shared TypeScript types live in `packages/shared-types/`, generated from the API's OpenAPI schema (committed to `apps/api/openapi.json` so generation is reproducible).

## Consequences

- Single PR can change schema + frontend type consumption atomically.
- Two package managers in the repo: developers must have both `pnpm` and `uv` installed. Documented in the root README.
- CI runs Node and Python pipelines in parallel jobs.
