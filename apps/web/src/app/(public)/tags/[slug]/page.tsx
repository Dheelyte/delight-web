import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";

import { Pagination, parsePage } from "@/components/pagination";
import { PostCard } from "@/components/public/post-card";
import { PublicApiError, publicFetch } from "@/lib/public-api";
import { breadcrumbsJsonLd, jsonLdScript } from "@/lib/seo/jsonld";
import { absoluteUrl } from "@/lib/site";
import type { SlugRedirectOut, TagDetailOut } from "@/lib/types";

export const revalidate = 60;

const PAGE_SIZE = 10;

async function loadTag(slug: string, page: number): Promise<TagDetailOut> {
  const offset = (page - 1) * PAGE_SIZE;
  try {
    return await publicFetch<TagDetailOut>(
      `/v1/public/tags/${slug}?limit=${PAGE_SIZE}&offset=${offset}`,
    );
  } catch (err) {
    if (err instanceof PublicApiError && err.status === 404) {
      try {
        const r = await publicFetch<SlugRedirectOut>(
          `/v1/public/slug-history/tag/${slug}`,
          { revalidate: 3600 },
        );
        permanentRedirect(`/tags/${r.new_slug}`);
      } catch (lookupErr) {
        if (lookupErr instanceof PublicApiError && lookupErr.status === 404) notFound();
        throw lookupErr;
      }
    }
    throw err;
  }
}

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = parsePage((await searchParams).page);
  try {
    const tag = await loadTag(slug, page);
    // Canonical points at *this* page, including `?page=N` — Appendix A: never
    // canonicalise paginated archives back to page 1.
    const canonical =
      page > 1
        ? absoluteUrl(`/tags/${tag.slug}?page=${page}`)
        : absoluteUrl(`/tags/${tag.slug}`);
    return {
      title: page > 1 ? `Tag: ${tag.name} — page ${page}` : `Tag: ${tag.name}`,
      description: `Posts tagged "${tag.name}".`,
      alternates: { canonical },
      // Thin index pages are noindex'd by default per Appendix A.
      robots: tag.posts.total < 3 ? "noindex, follow" : undefined,
    };
  } catch {
    return { title: "Tag" };
  }
}

export default async function TagPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const { slug } = await params;
  const page = parsePage((await searchParams).page);
  const tag = await loadTag(slug, page);
  const totalPages = Math.max(1, Math.ceil(tag.posts.total / PAGE_SIZE));

  return (
    <>
      {jsonLdScript(
        breadcrumbsJsonLd([
          { name: "Home", path: "/" },
          { name: `Tag: ${tag.name}`, path: `/tags/${tag.slug}` },
        ]),
      )}
      <main className="mx-auto w-full max-w-6xl px-6 py-12">
        <header>
          <p className="text-xs uppercase tracking-wider text-fg-subtle">Tag</p>
          <h1 className="mt-1 font-serif text-4xl">{tag.name}</h1>
          <p className="mt-2 text-sm text-fg-muted">
            {tag.posts.total} post{tag.posts.total === 1 ? "" : "s"}
            {totalPages > 1 ? ` · page ${page} of ${totalPages}` : ""}
          </p>
        </header>
        <div className="mt-8 max-w-3xl">
          {tag.posts.items.length === 0 ? (
            <p className="text-fg-muted">
              {page === 1
                ? "No posts under this tag yet."
                : "Nothing on this page."}
            </p>
          ) : (
            tag.posts.items.map((p) => <PostCard key={p.slug} post={p} />)
          )}
          <Pagination
            page={page}
            totalPages={totalPages}
            basePath={`/tags/${tag.slug}`}
          />
        </div>
      </main>
    </>
  );
}
