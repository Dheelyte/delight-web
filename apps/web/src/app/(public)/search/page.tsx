import type { Metadata } from "next";

import { Pagination, parsePage } from "@/components/pagination";
import { PostCard } from "@/components/public/post-card";
import { publicFetch } from "@/lib/public-api";
import type { SearchResults } from "@/lib/types";

// Search is request-shaped - do not cache aggressively.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Search",
  robots: "noindex, follow",
};

const PAGE_SIZE = 20;

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; page?: string }>;
}) {
  const sp = await searchParams;
  const q = sp.q ?? "";
  const page = parsePage(sp.page);

  let results: SearchResults | null = null;
  if (q.trim()) {
    const offset = (page - 1) * PAGE_SIZE;
    results = await publicFetch<SearchResults>(
      `/v1/public/search?q=${encodeURIComponent(q)}&limit=${PAGE_SIZE}&offset=${offset}`,
      { revalidate: false },
    );
  }

  const totalPages = results
    ? Math.max(1, Math.ceil(results.total / PAGE_SIZE))
    : 1;

  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-12">
      <h1 className="font-serif text-3xl">Search</h1>
      <form action="/search" className="mt-4 flex gap-2">
        <input
          type="search"
          name="q"
          defaultValue={q}
          autoFocus
          placeholder="Search posts"
          className="flex-1 rounded-md border border-border bg-bg px-3 py-2 text-sm focus:border-accent focus:outline-none"
        />
        {/* Submitting the form starts a fresh search - drop back to page 1. */}
        <button
          type="submit"
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-fg"
        >
          Search
        </button>
      </form>

      {results === null ? (
        <p className="mt-8 text-sm text-fg-muted">Type a query to search.</p>
      ) : (
        <section className="mt-6">
          <p className="text-sm text-fg-muted">
            {results.total} result{results.total === 1 ? "" : "s"} for{" "}
            <strong className="text-fg">&quot;{results.q}&quot;</strong>
            {totalPages > 1 ? ` · page ${page} of ${totalPages}` : ""}
          </p>
          <div className="mt-2">
            {results.items.length === 0 ? (
              <p className="mt-4 text-sm text-fg-muted">
                {page === 1 ? "No matches." : "Nothing on this page."}
              </p>
            ) : (
              results.items.map((p) => <PostCard key={p.slug} post={p} />)
            )}
          </div>
          <Pagination
            page={page}
            totalPages={totalPages}
            basePath="/search"
            params={{ q }}
          />
        </section>
      )}
    </main>
  );
}
