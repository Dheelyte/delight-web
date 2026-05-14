# web

Next.js 15 (App Router) frontend for Delight Web. Hosts the public reader-facing site and the `/admin` dashboard.

## Dev

```bash
pnpm install
pnpm --filter web dev
```

Visit http://localhost:3000.

## Scripts

- `pnpm --filter web dev` — dev server
- `pnpm --filter web build` — production build
- `pnpm --filter web lint` — eslint
- `pnpm --filter web typecheck` — `tsc --noEmit`
- `pnpm --filter web test` — vitest
