# 002 — Hosting: Vercel (web) + AWS Lambda (api)

- **Status:** accepted
- **Date:** 2026-05-13

## Context

The original build prompt called for Docker Compose locally and a single-VM / PaaS deployment. The addendum supersedes that: Vercel for the web, AWS Lambda for the API.

## Decision

- **Web → Vercel.** Next.js 15 ISR, edge middleware (CSP nonce, `/admin` gating, slug-history 301s), and OG image generation are first-party. Preview deployments per PR.
- **API → AWS Lambda** (container image, ARM64/Graviton, behind API Gateway HTTP API). FastAPI runs unchanged under the Lambda Web Adapter — no Mangum.
- **DB → Neon Postgres** by default (HTTP driver avoids Lambda pool issues, branch DB per Vercel preview). RDS + RDS Proxy documented as an alternative in a later ADR.
- **Async work → SQS + Lambda consumers + EventBridge Scheduler.** No Redis, no Celery, no worker fleet.
- **Email → AWS SES** in prod; Mailhog locally.
- **Edge limits → AWS WAF.**

Pricing math for a single-author blog with ~10k MAU: roughly free-tier across the board for the first year (Vercel hobby, Lambda free tier, Neon free tier, SES first 62k emails/month free from EC2).

## Consequences

- No always-on infra cost. Cold starts on the API (mitigated by lazy imports; provisioned concurrency only if admin Core Web Vitals regress).
- Local dev no longer needs Redis. `docker-compose.yml` ships Postgres + Mailhog only; SQS/EventBridge tested via `moto` in unit tests.
- `infra/` will hold an AWS CDK (TypeScript) app from Stage 8. Until then the api runs locally via `uvicorn`.
