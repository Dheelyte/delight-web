# Backup & restore

## Backup strategy

| Layer | What | How | Retention |
|---|---|---|---|
| Postgres | Full logical dump | `pg_dump` cron via Neon "Point-in-time recovery" (always on) or RDS automated backups | 7 days hot, 30 days cold |
| Cloudinary | Media assets | Cloudinary has its own redundancy; we never re-upload the same `public_id`, so deletions are the only loss vector | n/a |
| Outbox | Pending email / revalidate sends | Captured in DB dump | - |
| Code | Git | GitHub | forever |

## Daily snapshot - manual

```bash
# Neon: take an instant branch (free, point-in-time copy)
neonctl branches create --parent main --name snapshot-$(date +%Y%m%d)

# RDS: trigger a manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier delight-blog-prod \
  --db-snapshot-identifier delight-blog-$(date +%Y%m%d)

# Local dev: dump the compose Postgres to a file
docker compose exec postgres pg_dump -U blog -Fc blog > backups/blog-$(date +%Y%m%d).pgcustom
```

## Restore - local

```bash
# Wipe the current dev DB
docker compose exec postgres psql -U blog -d postgres \
  -c "DROP DATABASE IF EXISTS blog; CREATE DATABASE blog OWNER blog;"

# Restore from the latest custom-format dump
docker compose exec -T postgres pg_restore -U blog -d blog --clean --if-exists \
  < backups/blog-LATEST.pgcustom

# Sanity: alembic should already be at head; if it isn't, upgrade.
cd apps/api && uv run alembic upgrade head
```

## Restore - production

1. **Pause writes.** Set `MAINTENANCE_MODE=1` in the Vercel env (the layout
   shows a maintenance page when this is set) and redeploy.
2. **Branch from the target point-in-time.**
   - Neon: `neonctl branches create --parent main --timestamp '2026-01-01T13:30:00Z'`
   - RDS: `aws rds restore-db-instance-to-point-in-time ...`
3. **Verify** by running `psql` against the new branch and checking row counts
   for `users`, `posts`, `audit_log` against your expectations.
4. **Cut over.** Update the `DATABASE_URL` secret in AWS Secrets Manager (or
   Vercel for the web app), redeploy the API stack, and run smoke tests:
   `GET /api/v1/health`, sign-in, open a post.
5. **Resume writes.** Clear `MAINTENANCE_MODE` and redeploy.

## Drill cadence

- **Quarterly:** run a full restore against a staging branch, assert post
  counts, and tick the date in this file's footer.
- **Annually:** time the full restore and add the duration to the runbook so
  future-you knows the order of magnitude.

---

*Last drill:* (none yet - schedule one in Stage 8 once a production DB exists.)
