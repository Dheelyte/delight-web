# Handle a spam wave

A burst of comments or subscriber signups is the most common attack we'll see.
This runbook gets the firehose under control without taking the site down.

## 1. Confirm it's happening

```sql
-- Comment volume in the last hour
SELECT date_trunc('minute', created_at) AS m, count(*)
FROM comments
WHERE created_at > now() - interval '1 hour'
GROUP BY 1 ORDER BY 1 DESC;

-- Top IP-hash buckets
SELECT ip_hash, count(*)
FROM comments
WHERE created_at > now() - interval '1 hour'
GROUP BY ip_hash ORDER BY count(*) DESC LIMIT 20;

-- Auth-attempt spikes
SELECT kind, identifier, count(*)
FROM auth_attempts
WHERE attempted_at > now() - interval '1 hour' AND succeeded = false
GROUP BY 1, 2 ORDER BY count(*) DESC LIMIT 20;
```

## 2. Lock the front door

Pick the loudest signal and tighten it:

```sql
-- Bulk-mark recent same-IP comments as spam
UPDATE comments
SET status = 'spam'
WHERE ip_hash IN (SELECT ip_hash FROM comments
                  WHERE created_at > now() - interval '1 hour'
                  GROUP BY ip_hash HAVING count(*) > 5);
```

For subscriber spam (rare since we removed double opt-in, but possible):

```sql
DELETE FROM subscribers
WHERE created_at > now() - interval '1 hour'
  AND (
    email LIKE '%@mailinator.com'
    OR email LIKE '%@tempmail.%'
  );
```

## 3. Tighten the rate limit

Cut the auth-attempt budget while the wave is active. Edit
`apps/api/app/services/throttle.py`:

```python
SHORT_MAX_FAILURES = 2   # was 5
LONG_MAX_FAILURES  = 5   # was 20
```

Redeploy the API. The limits restore on next deploy after the wave passes.

## 4. Block at the edge

If the source is a small set of IPs, push the block out of the application:

- **Vercel:** Project → Firewall → IP Blocking → add the CIDRs.
- **AWS API Gateway in front of Lambda:** add a WAF IP-set rule (CDK in
  `infra/api-stack.ts` — see Stage 8).

## 5. Audit the cleanup

```sql
-- Confirm the spam wave is no longer in the queue
SELECT status, count(*) FROM comments
WHERE created_at > now() - interval '24 hours' GROUP BY status;

-- Confirm the rate-limit table reflects the wave being throttled
SELECT identifier, kind, succeeded, count(*)
FROM auth_attempts
WHERE attempted_at > now() - interval '1 hour'
GROUP BY 1,2,3 ORDER BY count(*) DESC LIMIT 20;
```

## 6. Post-incident

- Note the source IPs, vectors, and the volume in `docs/incidents/YYYY-MM-DD.md`.
- If the heuristics in `app/services/comments.py` missed the wave, raise the
  `MAX_URLS_IN_BODY` ceiling or add a new pattern check — file a PR with a
  test that reproduces a sample payload.
