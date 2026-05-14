import Link from "next/link";

import { NewPostButton } from "@/components/admin/new-post-button";
import { Pagination, parsePage } from "@/components/pagination";
import { apiFetch } from "@/lib/api";
import type { PostList, PostStatus } from "@/lib/types";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 20;

const STATUS_TABS: { label: string; value: PostStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Draft", value: "draft" },
  { label: "Published", value: "published" },
  { label: "Archived", value: "archived" },
];

function fmtDate(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString();
}

export default async function PostsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; q?: string; page?: string }>;
}) {
  const params = await searchParams;
  const status = (params.status ?? "all") as PostStatus | "all";
  const q = params.q ?? "";
  const page = parsePage(params.page);

  const search = new URLSearchParams();
  search.set("limit", String(PAGE_SIZE));
  search.set("offset", String((page - 1) * PAGE_SIZE));
  if (status !== "all") search.set("status", status);
  if (q) search.set("q", q);

  const { data } = await apiFetch<PostList>(`/v1/posts?${search.toString()}`);
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="font-serif text-3xl">Posts</h1>
        <NewPostButton />
      </header>

      {/* Changing the query or status resets to page 1 - neither the form nor
          the status tabs carry `page`, so navigating drops it. */}
      <form className="flex flex-wrap items-center gap-2" action="/admin/posts">
        <input
          type="search"
          name="q"
          defaultValue={q}
          placeholder="Search title or slug"
          className="w-64 rounded-md border border-border bg-bg px-3 py-1.5 text-sm focus:border-accent focus:outline-none"
        />
        <input type="hidden" name="status" value={status} />
        <button
          type="submit"
          className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-bg-muted"
        >
          Search
        </button>
        <nav className="ml-auto flex gap-1">
          {STATUS_TABS.map((tab) => (
            <Link
              key={tab.value}
              href={
                tab.value === "all"
                  ? "/admin/posts"
                  : `/admin/posts?status=${tab.value}`
              }
              className={
                "rounded-md border px-3 py-1.5 text-sm " +
                (status === tab.value
                  ? "border-accent bg-accent text-accent-fg"
                  : "border-border text-fg-muted hover:bg-bg-muted")
              }
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </form>

      <div className="overflow-x-auto rounded-lg border border-border bg-bg-elevated">
        <table className="w-full text-sm">
          <thead className="border-b border-border text-left text-xs uppercase text-fg-muted">
            <tr>
              <th className="px-4 py-2 font-medium">Title</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Updated</th>
              <th className="px-4 py-2 font-medium">Published</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-fg-muted">
                  {page === 1 ? "No posts." : "Nothing on this page."}
                </td>
              </tr>
            )}
            {data.items.map((p) => (
              <tr key={p.id} className="hover:bg-bg-muted">
                <td className="px-4 py-2">
                  <Link
                    href={`/admin/posts/${p.id}/edit`}
                    className="font-medium hover:underline"
                  >
                    {p.title}
                  </Link>
                  <div className="text-xs text-fg-subtle">{p.slug}</div>
                </td>
                <td className="px-4 py-2">
                  <span className="rounded-full border border-border px-2 py-0.5 text-xs text-fg-muted">
                    {p.status}
                  </span>
                </td>
                <td className="px-4 py-2 text-xs text-fg-muted">
                  {fmtDate(p.updated_at)}
                </td>
                <td className="px-4 py-2 text-xs text-fg-muted">
                  {fmtDate(p.published_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-fg-subtle">
        {data.total} post{data.total === 1 ? "" : "s"}
        {totalPages > 1 ? ` · page ${page} of ${totalPages}` : ""}
      </p>

      <Pagination
        page={page}
        totalPages={totalPages}
        basePath="/admin/posts"
        params={{ status: status === "all" ? undefined : status, q }}
      />
    </div>
  );
}
