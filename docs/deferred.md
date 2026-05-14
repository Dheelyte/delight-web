# Deferred work

Intentional scope cuts from each stage. The reason each item is deferred matters more than the item itself — these are not TODOs to clean up later, they are decisions to revisit only if the listed condition holds.

## Stage 7

- **Live `securityheaders.com` A+ verification.** The middleware and `vercel.json` both ship the required headers; verifying the grade against a real deployed URL belongs to Stage 8 once the site is on a public domain.
- **CSP report-uri.** The CSP is enforcing-only; we do not yet collect violation reports. Wire up a tiny `/api/v1/csp-report` endpoint that drops bodies into the `audit_log` if/when we discover CSP regressions in the wild.
- **Provisioned concurrency on the API Lambda.** Skipped until the admin actually feels the cold-start tax. Lazy imports already keep cold starts under ~500 ms.
- **Materialised view for top-posts.** [`docs/perf.md`](perf.md) flags this — only worth doing when `page_views` rows climb past ~1M.
- **Real load-test report.** [`scripts/load_test.js`](../scripts/load_test.js) is ready to run; the actual recorded p95 numbers belong in a Stage 8 PR once the site is live.
- **Synthetic monitoring on a hosted uptime service.** Pingdom / Better Uptime / a Cloudflare healthcheck — Stage 8 when the production URL exists.
- **`MAINTENANCE_MODE` flag.** [Backup runbook](runbooks/backup-restore.md) references it for cutover but the layout doesn't yet read the env var. Add when the first prod restore drill is scheduled.

## Stage 5

- ~~**Inline images don't currently use the responsive pipeline.**~~ **Resolved.** `lib/inline-images.ts` (`optimizeInlineImages`) post-processes `content_html` server-side on the post detail page — Cloudinary `<img>` URLs get `f_auto,q_auto` + a width `srcset` + `sizes` + lazy loading. Remaining gap: no explicit `width`/`height`, so inline images that CKEditor didn't size can still cause CLS — fixable only with real dimensions, which the HTML string doesn't carry.
- **True blurhash.** The LQIP is a 24×24 JPEG (~1.5 KB) drawn client-side. Real blurhash would be ~30 bytes. Storage cost is negligible for the foreseeable future; switch when traffic justifies the perceptible difference.
- **Cover-image cropping preview.** The focal-point picker shows where Cloudinary will centre the crop, but it doesn't render an actual cropped preview at different aspect ratios. Add a small "1200×630 preview" thumbnail using `cloudinaryUrl(..., {fit: 'fill', width: 200, height: 105})` once the social-card use case warrants it.
- **Image upload progress.** The current uploader is binary (busy / not busy). For larger uploads a real progress bar via `XMLHttpRequest` would help; not worth the complexity until covers grow beyond a few hundred KB after Cloudinary processing.
- **`PATCH /media/{id}` ownership check.** Any editor can edit any media row. Acceptable today; once we have multiple editors with overlapping work, restrict to admin or uploader.

## Stage 4

- **On-demand revalidation is wired but not called.** [`apps/api/app/services/revalidate.py`](apps/api/app/services/revalidate.py) and [`apps/web/src/app/api/revalidate/route.ts`](apps/web/src/app/api/revalidate/route.ts) both exist; the posts service does not yet invoke the helper from `publish` / `unpublish` / etc. Wiring it in via FastAPI `BackgroundTasks` is one line per route. Deliberately deferred so the test suite doesn't make outbound HTTP calls. ISR's time-based revalidation (60s / 300s) is the safety net until then.
- **Sticky TOC sidebar on post pages.** Spec asks for one at `xl+` breakpoints. Requires parsing `content_html` for `<h2>`/`<h3>` either server-side (Python) or client-side (DOM). Cleanest: emit a `headings` array from the renderer in Stage 5.
- **Share rail.** Skipped — copy-link is one button and we don't want to ship social-platform-specific buttons until the audience exists.
- **Per-post FAQ / HowTo / Person JSON-LD.** Spec lists these in Appendix A. We ship `WebSite`, `Organization`, `BlogPosting`, `BreadcrumbList` — the four that affect every page. Per-post conditional schemas come with the matching TipTap extensions in a later stage.
- **Image sitemap entries (`<image:image>`).** The sitemap is plain `urlset` for now. Add once cover-image rendering lands.
- **Per-locale alternates.** Single-locale site; `hreflang` not needed.
- **Lighthouse ≥95 verification.** Cannot run from this environment. Local check + CI Lighthouse action is a Stage 7 hardening task.
- **Search ranking polish.** `plainto_tsquery` is the simplest decent default. `websearch_to_tsquery` (handles quoted phrases, `-foo` exclusion) is a one-line swap when search usage grows.

## Stage 3

- **Command palette (⌘K).** Not implemented; the spec calls for it, but the surface area is small enough that the sidebar nav + ⌘S explicit save covers daily use today. Add when the admin acquires >10 navigable destinations.
- **Slash-command (`/`) menu, drag handles, distraction-free mode.** Editor ships with a top toolbar instead. The toolbar covers every block-level operation from the spec; the slash menu is a UX nicety, not new capability.
- **Markdown shortcut input rules** (`# `, `## `, `> `, `- `, `1. `). TipTap's StarterKit ships its own; not yet customised.
- **Footnotes, KaTeX (inline LaTeX), generic oEmbed embeds, tables.** Renderer + sanitiser allowlist already support `<table>`, but the editor UI for inserting tables / footnotes / formulae is deferred. Embeds beyond images need TipTap node extensions per provider.
- **Side-by-side revision diff view.** The history endpoint and `restore` action work; the UI lists revisions and restores by id, but no visual diff. Add `diff-match-patch` when the volume of revisions justifies it.
- **Cover image focal-point cropping.** The `CoverImageUploader` inserts images into the body; the dedicated `cover_image_id` slot is wired in the schema and metadata API but not the UI.
- **Bulk actions (archive / delete) on the posts list.** Single-row actions are available from the editor; bulk is a Stage-4-onward usability tweak.
- **TipTap-server-side render parity.** The Python renderer (`app/services/render.py`) covers everything the editor can emit *today*. As we add extensions (footnotes, embeds), they must land in the renderer at the same time.

## Stage 2

- **Email delivery for password reset / invites.** The service produces the signed token and writes the audit row, but no email is sent yet. Outbox + SES wiring lands in Stage 6. For now, recover tokens from the audit log or test fixtures.
- **TOTP "pending vs active" split.** `/auth/totp/enroll` stores the encrypted secret immediately rather than gating it behind a verify step. This is safe because no flow yet *requires* TOTP for non-login operations; the verify endpoint exists for the UI to confirm enrolment. A `totp_pending_secret_encrypted` column is the obvious clean-up for Stage 3.
- **TOTP replay cache is in-process.** Fine for a single Lambda warm container; consolidates into a tiny DB-backed table the first time we run more than one concurrent worker.
- **No CSRF token.** `SameSite=Lax` plus same-origin proxy plus CORS allowlist covers the threat. If we ever expose the API directly to a different origin we add a double-submit token.
- **Admin invite UI.** API endpoint exists (`POST /api/v1/auth/users`); the form is part of the Stage 3 admin shell.

## Stage 1

- **`page_views` month partitions** — only the default partition is created in the initial migration. Month-rollover partition creation is a beat-style Lambda introduced alongside analytics in Stage 6.
- **Authorisation logic** — the `role` column exists but no `require_role()` dependency yet. Stage 2.
- **TOTP encryption** — `users.totp_secret_encrypted` column exists, but Fernet-from-SECRET_KEY helper is deferred to Stage 2 when 2FA enrolment is built.
- **Sanitiser on `posts.content_html`** — the column accepts whatever is written. Stage 3 introduces the nh3 server-side sanitisation pass.

## Stage 0

- **No Vercel project linked yet.** The web app builds locally and in CI; the production Vercel project is created in Stage 8. Revisit when the first preview deployment is needed.
- **No CDK app yet.** `infra/` is empty. Stage 8 introduces the CDK stacks.
- **No `packages/shared-types` content.** The OpenAPI schema doesn't exist yet (Stage 2 onward); generation is wired in once there are routes to describe.
- **No seed script.** Seed data lives in Stage 1, alongside the schema it depends on.
- **No Playwright / E2E suite.** End-to-end paths require a real auth flow and post pipeline — set up in Stage 4 after the public site renders something meaningful.
- **No domain or TLS.** Defer to Stage 8 deployment.
- **No Sentry / GlitchTip wiring.** Add once the app is doing something worth instrumenting (Stage 2 onward).
