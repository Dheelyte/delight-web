import Link from "next/link";

import { apiFetch } from "@/lib/api";
import type { AnalyticsWindow, PostList } from "@/lib/types";

export const dynamic = "force-dynamic";

interface ModerationCount {
  pending: number;
}
interface SubscriberCount {
  confirmed: number;
}

export default async function AdminDashboard() {
  const [{ data: recent }, { data: pending }, { data: subs }, { data: analytics }] =
    await Promise.all([
      apiFetch<PostList>("/v1/posts?limit=5"),
      apiFetch<ModerationCount>("/v1/comments/count"),
      apiFetch<SubscriberCount>("/v1/subscribers/count"),
      apiFetch<AnalyticsWindow>("/v1/analytics?window=30"),
    ]);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-serif text-3xl">Dashboard</h1>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <Stat
          label="Pending comments"
          value={pending.pending}
          href="/admin/comments"
          highlight={pending.pending > 0}
        />
        <Stat
          label="Confirmed subscribers"
          value={subs.confirmed}
          href="/admin/subscribers?status=confirmed"
        />
        <Stat
          label="Views (last 30d)"
          value={analytics.top_posts.reduce((acc, p) => acc + p.views, 0)}
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card title="Recent posts" href="/admin/posts">
          <ul className="divide-y divide-border">
            {recent.items.length === 0 && (
              <li className="py-3 text-sm text-fg-muted">No posts yet.</li>
            )}
            {recent.items.map((p) => (
              <li
                key={p.id}
                className="flex items-center justify-between py-3 text-sm"
              >
                <Link
                  href={`/admin/posts/${p.id}/edit`}
                  className="truncate hover:underline"
                >
                  {p.title}
                </Link>
                <span className="rounded-full border border-border px-2 py-0.5 text-xs text-fg-muted">
                  {p.status}
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Top posts (30d)">
          <ul className="divide-y divide-border">
            {analytics.top_posts.length === 0 && (
              <li className="py-3 text-sm text-fg-muted">
                No view data yet — visit a published post in another tab to seed it.
              </li>
            )}
            {analytics.top_posts.map((p) => (
              <li
                key={p.slug}
                className="flex items-center justify-between py-3 text-sm"
              >
                <Link href={`/posts/${p.slug}`} className="truncate hover:underline">
                  {p.title}
                </Link>
                <span className="font-mono text-xs text-fg-muted">{p.views}</span>
              </li>
            ))}
          </ul>
        </Card>
      </section>

      {analytics.top_referrers.length > 0 && (
        <Card title="Top referrers (30d)">
          <ul className="divide-y divide-border">
            {analytics.top_referrers.map((r) => (
              <li
                key={r.host}
                className="flex items-center justify-between py-2 text-sm"
              >
                <span className="font-mono text-fg-muted">{r.host}</span>
                <span className="font-mono text-xs text-fg-muted">{r.views}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  href,
  highlight = false,
}: {
  label: string;
  value: number;
  href?: string;
  highlight?: boolean;
}) {
  const card = (
    <div
      className={
        "rounded-lg border bg-bg-elevated p-4 " +
        (highlight ? "border-accent" : "border-border")
      }
    >
      <div className="text-xs uppercase tracking-wider text-fg-subtle">{label}</div>
      <div className="mt-1 font-serif text-3xl">{value.toLocaleString()}</div>
    </div>
  );
  return href ? <Link href={href}>{card}</Link> : card;
}

function Card({
  title,
  href,
  children,
}: {
  title: string;
  href?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border bg-bg-elevated p-4">
      <header className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-fg-muted">{title}</h2>
        {href && (
          <Link href={href} className="text-xs text-accent hover:underline">
            View all
          </Link>
        )}
      </header>
      {children}
    </section>
  );
}
