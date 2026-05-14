# Performance review checklist

The schema ships with the indexes the workload actually needs ([initial migration](../apps/api/alembic/versions/20260513_0001_initial_schema.py));
this doc captures the queries to keep an eye on and how to verify them.

## Hot paths to verify

Run each with `EXPLAIN (ANALYZE, BUFFERS)` after seeding realistic data
(~1000 posts, ~10k comments, ~50k page_views).

### Homepage feed

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM posts
WHERE status = 'published' AND published_at <= now()
ORDER BY published_at DESC NULLS LAST
LIMIT 10;
```

Expected: index scan on `ix_posts_published_at_desc`. p95 < 5 ms on warm cache.

### Single post by slug

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM posts WHERE slug = 'hello-world';
```

Expected: unique-index lookup. p95 < 1 ms.

### Search

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, ts_rank(search_vector, q) AS rank
FROM posts, plainto_tsquery('english', 'stack') q
WHERE status = 'published'
  AND search_vector @@ q
ORDER BY rank DESC, published_at DESC
LIMIT 20;
```

Expected: bitmap heap scan via `ix_posts_search_vector` (GIN). p95 < 20 ms
even on 100k rows.

### Comments per post

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM comments
WHERE post_id = $1 AND status = 'approved'
ORDER BY created_at ASC;
```

Expected: index scan on `ix_comments_post_id_status_created_at`.

### Top posts (analytics)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT post_id, count(*) AS views
FROM page_views
WHERE viewed_at >= now() - interval '30 days'
GROUP BY post_id
ORDER BY views DESC
LIMIT 10;
```

Expected: index scan on `ix_page_views_viewed_at` then HashAggregate. If this
exceeds ~100 ms at expected scale, materialise into a daily rollup table.

## Cache layers

- **Vercel/CDN:** `Cache-Control: public, s-maxage=60, stale-while-revalidate=300`
  on list endpoints, `s-maxage=300` on post detail (see [`apps/api/app/api/v1/public.py`](../apps/api/app/api/v1/public.py)).
- **Next.js ISR:** 60 s for lists, 300 s for post pages. On-demand revalidation
  via `/api/revalidate` flips both within a second of publish.
- **No in-app cache.** Per [ADR 002](decisions/002-stack-vercel-aws.md) we
  serve anonymous reads from the edge; the API is rarely hit for them.

## Load test

[`scripts/load_test.js`](../scripts/load_test.js) is a small k6 script that
hammers the public surface. Run it from a separate machine:

```bash
k6 run -e BASE=https://<your-domain> --vus 50 --duration 2m scripts/load_test.js
```

Target: 100 req/s sustained homepage, p95 < 100 ms (warm CDN cache),
< 0.1% errors. Anything worse merits investigation.
