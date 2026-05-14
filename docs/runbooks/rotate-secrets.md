# Rotate secrets

Run this quarterly, or immediately on any suspected compromise.

## Inventory

| Secret | Where it lives | Rotation impact |
|---|---|---|
| `SECRET_KEY` | API env (Vercel/AWS) | **Invalidates all sessions, reset tokens, encrypted TOTP secrets.** TOTP-enrolled users must re-enrol. |
| Postgres password | DB provider + API env | Brief connection failures while the secret propagates. |
| Cloudinary `API_SECRET` | API env | Existing media URLs keep working; new uploads need the new secret. |
| SMTP / SES credentials | API env | New mail send only - in-flight outbox rows retry on next worker tick. |
| `REVALIDATE_SECRET` | Both API and web envs | Must update **both** in lockstep; otherwise revalidation calls 403. |
| GitHub Actions deploy keys | GitHub repo secrets | Deploys fail until the new key is in place. |

## Standard procedure

1. **Generate the new value.**

   ```bash
   # 32+ bytes, URL-safe
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. **Stage the new value in the secret store** without removing the old one,
   if the platform supports two-key rotation (Cloudinary, SES). Otherwise
   prepare to write the new value in step 4.

3. **Smoke-test on staging** with the new value in place.

4. **Cut over production.**
   - **Single-key services** (`SECRET_KEY`, DB password): update the secret
     store, redeploy the API, then redeploy the web app if it shares the value
     (e.g. `REVALIDATE_SECRET`). Both apps must restart for the new env to
     take effect on Lambda / Vercel.
   - **Dual-key services** (Cloudinary): rotate the active key, wait one
     deploy cycle, then revoke the old key.

5. **Verify post-rotation.**
   - `curl /api/v1/health` returns 200.
   - Sign in to `/admin` (a fresh sign-in confirms session signing works).
   - Trigger an ISR revalidation from the API and confirm `/api/revalidate`
     accepts it (Vercel logs show 200, not 403).
   - Upload a new image (validates Cloudinary signing).

6. **Record the rotation** in the audit log (the API auto-logs login + media
   events; add a manual `audit_log` row for the rotation itself):

   ```sql
   INSERT INTO audit_log (id, action, resource_type, resource_id, metadata)
   VALUES (
     gen_random_uuid(), 'secret.rotated', 'secret', 'SECRET_KEY',
     jsonb_build_object('by', '<your name>', 'at', now()::text)
   );
   ```

## Disaster path - suspected compromise

1. Rotate **immediately** (skip staging).
2. Force every user out: `DELETE FROM sessions;` then bump `SECRET_KEY` so
   any still-cached cookies fail validation.
3. Audit `audit_log` for unexpected `auth.login` rows or unfamiliar IPs in the
   24h before the suspected compromise.
4. Send a transparency note to active editors via the admin email pathway.

---

*Last rotation:* (none yet)
