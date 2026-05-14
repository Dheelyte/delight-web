# Deploy & rollback

## Normal deploy

```bash
git tag v$(date +%Y.%m.%d)-$(git rev-parse --short HEAD)
git push --tags
```

GitHub Actions:

1. `deploy-api.yml` builds the FastAPI container, pushes to ECR, and runs
   `cdk deploy ApiStack` with a manual approval gate.
2. Vercel's GitHub integration deploys the web app on every push to `main`;
   the tag itself doesn't trigger Vercel.
3. `alembic upgrade head` runs as a one-off Lambda invocation **before** the
   API Lambda swaps to the new container image. If the migration fails the
   deploy aborts and the previous image keeps serving.

## Verify

```bash
# Health
curl -fsSL https://api.<your-domain>/api/v1/health | jq

# A published post round-trip
curl -fsSL https://<your-domain>/posts/hello-world | grep -q '<title>'

# OG + JSON-LD present
curl -s https://<your-domain>/posts/hello-world | \
  grep -E '(og:title|application/ld\+json)'
```

## Roll back the web app

Vercel keeps every deployment. Two paths:

1. **One-click:** Vercel dashboard → Project → Deployments → pick a previous
   deployment → "Promote to production".
2. **CLI:**
   ```bash
   vercel rollback <deployment-url> --token=$VERCEL_TOKEN
   ```

## Roll back the API

The Lambda alias points at a specific container-image tag. CDK keeps the
previous image in ECR; switching the alias is a single command:

```bash
aws lambda update-alias \
  --function-name delight-blog-api \
  --name live \
  --function-version <PREVIOUS_VERSION>
```

If the bad release **also ran a schema migration**, see "Migration rollback"
below first — flipping the Lambda alone won't undo a destructive migration.

## Migration rollback

```bash
# Identify the bad revision
uv run alembic history | head

# Step down one revision
uv run alembic downgrade -1

# Or jump to a known-good tag
uv run alembic downgrade <revision-id>
```

If the bad migration dropped a column or table:

1. Restore the affected rows from the most recent backup
   (see [backup-restore.md](./backup-restore.md)).
2. Run a custom one-shot migration that re-creates the schema element and
   re-inserts the rows. Treat this as a hotfix migration on a fresh revision.

**Two-phase rule of thumb:** any migration that drops data must be split into
"deprecate (stop writing)" → "backfill / dual-write" → "drop". Never deploy a
single revision that both stops writing and drops data.

## Killswitch

If something is on fire and you need everything to stop now:

1. **Web:** Vercel dashboard → Project Settings → Pause deployment.
2. **API:** Reduce the Lambda's reserved concurrency to `0`. All requests will
   return 429 with a Lambda-level error.
   ```bash
   aws lambda put-function-concurrency \
     --function-name delight-blog-api \
     --reserved-concurrent-executions 0
   ```
3. **DB:** Don't touch unless data integrity is in question; the API can be
   stopped without it.

Bring things back online in reverse order: DB → API → Web.
