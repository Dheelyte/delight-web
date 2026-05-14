import { Pagination, parsePage } from "@/components/pagination";
import { apiFetch } from "@/lib/api";
import type { SubscriberList } from "@/lib/types";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 50;
const STATUSES = ["all", "pending", "confirmed", "unsubscribed"] as const;

export default async function AdminSubscribersPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; page?: string }>;
}) {
  const params = await searchParams;
  const status = STATUSES.includes(params.status as never)
    ? (params.status as (typeof STATUSES)[number])
    : "all";
  const page = parsePage(params.page);
  const offset = (page - 1) * PAGE_SIZE;

  const { data } = await apiFetch<SubscriberList>(
    `/v1/subscribers?status=${status}&limit=${PAGE_SIZE}&offset=${offset}`,
  );
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      <h1 className="font-serif text-3xl">Subscribers</h1>
      {/* Status tabs omit `page`, so switching filter resets to page 1. */}
      <nav className="flex gap-1 text-sm">
        {STATUSES.map((s) => (
          <a
            key={s}
            href={`/admin/subscribers?status=${s}`}
            className={
              "rounded-md border px-3 py-1.5 capitalize " +
              (status === s
                ? "border-accent bg-accent text-accent-fg"
                : "border-border text-fg-muted hover:bg-bg-muted")
            }
          >
            {s}
          </a>
        ))}
      </nav>
      <div className="overflow-x-auto rounded-lg border border-border bg-bg-elevated">
        <table className="w-full text-sm">
          <thead className="border-b border-border text-left text-xs uppercase text-fg-muted">
            <tr>
              <th className="px-4 py-2 font-medium">Email</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Confirmed</th>
              <th className="px-4 py-2 font-medium">Joined</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-fg-muted">
                  {page === 1
                    ? "No subscribers in this view."
                    : "Nothing on this page."}
                </td>
              </tr>
            )}
            {data.items.map((s) => (
              <tr key={s.id} className="hover:bg-bg-muted">
                <td className="px-4 py-2 font-mono">{s.email}</td>
                <td className="px-4 py-2">
                  <span className="rounded-full border border-border px-2 py-0.5 text-xs text-fg-muted">
                    {s.status}
                  </span>
                </td>
                <td className="px-4 py-2 text-xs text-fg-muted">
                  {s.confirmed_at
                    ? new Date(s.confirmed_at).toLocaleString()
                    : "-"}
                </td>
                <td className="px-4 py-2 text-xs text-fg-muted">
                  {new Date(s.created_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-fg-subtle">
        {data.total} total
        {totalPages > 1 ? ` · page ${page} of ${totalPages}` : ""}
      </p>
      <Pagination
        page={page}
        totalPages={totalPages}
        basePath="/admin/subscribers"
        params={{ status: status === "all" ? undefined : status }}
      />
    </div>
  );
}
