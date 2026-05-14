import Link from "next/link";

import { cn } from "@/lib/cn";

interface Props {
  /** Current page, 1-indexed. */
  page: number;
  totalPages: number;
  /** Path without query string, e.g. "/tags/engineering" or "/admin/posts". */
  basePath: string;
  /** Extra query params to preserve on every page link (e.g. { q, status }). */
  params?: Record<string, string | number | undefined | null>;
}

/**
 * URL-based pagination. Server component - it's just `<Link>`s, no state.
 *
 * Page 1 links omit `?page=1` entirely so the bare URL stays canonical.
 * Renders all numbers up to 7 pages; beyond that, windows around the current
 * page with ellipses (1 … 4 5 6 … 20).
 */
export function Pagination({ page, totalPages, basePath, params = {} }: Props) {
  if (totalPages <= 1) return null;

  const href = (p: number): string => {
    const sp = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
    }
    if (p > 1) sp.set("page", String(p));
    const qs = sp.toString();
    return qs ? `${basePath}?${qs}` : basePath;
  };

  const items = pageWindow(page, totalPages);

  return (
    <nav
      aria-label="Pagination"
      className="mt-10 flex flex-wrap items-center justify-center gap-1"
    >
      <PageLink href={href(page - 1)} disabled={page <= 1} ariaLabel="Previous page">
        ← Prev
      </PageLink>

      {items.map((it, i) =>
        it === "…" ? (
          <span
            key={`gap-${i}`}
            aria-hidden="true"
            className="px-2 text-sm text-fg-subtle"
          >
            …
          </span>
        ) : (
          <PageLink
            key={it}
            href={href(it)}
            current={it === page}
            ariaLabel={`Page ${it}`}
          >
            {it}
          </PageLink>
        ),
      )}

      <PageLink
        href={href(page + 1)}
        disabled={page >= totalPages}
        ariaLabel="Next page"
      >
        Next →
      </PageLink>
    </nav>
  );
}

function PageLink({
  href,
  children,
  disabled = false,
  current = false,
  ariaLabel,
}: {
  href: string;
  children: React.ReactNode;
  disabled?: boolean;
  current?: boolean;
  ariaLabel?: string;
}) {
  const base =
    "inline-flex min-w-9 items-center justify-center rounded-md border px-3 py-1.5 text-sm";

  if (disabled) {
    return (
      <span
        aria-disabled="true"
        className={cn(base, "border-border text-fg-subtle opacity-40")}
      >
        {children}
      </span>
    );
  }
  if (current) {
    return (
      <span
        aria-current="page"
        className={cn(base, "border-accent bg-accent font-medium text-accent-fg")}
      >
        {children}
      </span>
    );
  }
  return (
    <Link
      href={href}
      aria-label={ariaLabel}
      className={cn(base, "border-border text-fg-muted hover:bg-bg-muted hover:text-fg")}
    >
      {children}
    </Link>
  );
}

/** [1,2,3,…] for small counts; [1,"…",4,5,6,"…",20] windowed for large. */
function pageWindow(current: number, total: number): (number | "…")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const wanted = new Set<number>([
    1,
    total,
    current - 1,
    current,
    current + 1,
  ]);
  const sorted = [...wanted]
    .filter((p) => p >= 1 && p <= total)
    .sort((a, b) => a - b);

  const out: (number | "…")[] = [];
  let prev = 0;
  for (const p of sorted) {
    if (p - prev > 1) out.push("…");
    out.push(p);
    prev = p;
  }
  return out;
}

/** Helper for pages: clamp a raw `?page=` value to a valid 1-indexed integer. */
export function parsePage(raw: string | undefined): number {
  const n = Number(raw);
  return Number.isInteger(n) && n >= 1 ? n : 1;
}
