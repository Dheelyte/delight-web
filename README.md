# Delight Web

Production-grade blog platform - public reader-facing site and a custom admin dashboard.

- **Web:** Next.js 15 (App Router, TS strict) on Vercel
- **API:** FastAPI (Python 3.12, async SQLAlchemy 2, Pydantic v2) on AWS Lambda
- **Data:** Postgres 16 (Neon in prod) + AWS SQS / EventBridge for async work
- **Media:** Cloudinary (signed uploads, AVIF/WebP responsive pipeline)

See [`docs/decisions/`](docs/decisions/) for architectural rationale and [`docs/deferred.md`](docs/deferred.md) for what is intentionally not yet built.

## 60-second quick start

Prerequisites: Node 20+, pnpm 10+, Python 3.12, `uv`, Docker.

```bash
git clone <this-repo>
cd delight-blog

# 1. Secrets
cp .env.example .env
# edit SECRET_KEY (python -c "import secrets; print(secrets.token_urlsafe(48))")

# 2. Infra (Postgres + Mailhog)
docker compose up -d

# 3. Frontend
pnpm install
pnpm --filter web dev          # http://localhost:3000

# 4. Backend (new terminal)
cd apps/api
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000/docs
```

Health: <http://localhost:8000/api/v1/health>.

Mailhog UI for inspecting outbound mail: <http://localhost:8025>.

## Repo layout

```
apps/
  web/       Next.js 15 - public site + /admin
  api/       FastAPI - domain / infra / services / api / workers
packages/
  shared-types/   TS types generated from the API's OpenAPI schema
infra/           AWS CDK (TypeScript) - Stage 8
docs/
  decisions/     ADRs
  runbooks/      Restore, rotate-secrets, deploy-rollback, etc.
  deferred.md    Things intentionally not implemented yet
```

The backend follows a light hexagonal split: `domain` (pure Python, no framework imports), `infra` (DB / Cloudinary / email adapters), `services` (use-cases), `api` (thin HTTP). Business logic must not leak into routers.

## Quality gates

Every change must pass:

| Check | Command |
|---|---|
| Web lint | `pnpm --filter web lint` |
| Web types | `pnpm --filter web typecheck` |
| Web tests | `pnpm --filter web test` |
| API lint | `cd apps/api && uv run ruff check . && uv run ruff format --check .` |
| API types | `cd apps/api && uv run mypy app` |
| API tests | `cd apps/api && uv run pytest` |
| Secrets   | `pre-commit run --all-files` |

CI runs all of the above on every PR.

## Build stages

The platform is built in eight numbered stages - see the original build prompt. Stage 0 (this commit) covers scaffolding and quality gates only; Stage 1 introduces the data model and migrations. Each stage ends with a status report and a manual review before the next begins.

## Commit hygiene

Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`). One logical change per commit. No secrets, no `.env`, no build artefacts. Every change goes through a PR.
