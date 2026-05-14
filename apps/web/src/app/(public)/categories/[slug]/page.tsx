import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";

import { Pagination, parsePage } from "@/components/pagination";
import { PostCard } from "@/components/public/post-card";
import { PublicApiError, publicFetch } from "@/lib/public-api";
import { breadcrumbsJsonLd, jsonLdScript } from "@/lib/seo/jsonld";
import { absoluteUrl } from "@/lib/site";
import type { CategoryDetailOut, SlugRedirectOut } from "@/lib/types";

export const revalidate = 60;

const PAGE_SIZE = 10;

async function loadCategory(
  slug: string,
  page: number,
): Promise<CategoryDetailOut> {
  const offset = (page - 1) * PAGE_SIZE;
  try {
    return await publicFetch<CategoryDetailOut>(
      `/v1/public/categories/${slug}?limit=${PAGE_SIZE}&offset=${offset}`,
    );
  } catch (err) {
    if (err instanceof PublicApiError && err.status === 404) {
      try {
        const r = await publicFetch<SlugRedirectOut>(
          `/v1/public/slug-history/category/${slug}`,
          { revalidate: 3600 },
        );
        permanentRedirect(`/categories/${r.new_slug}`);
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
    const cat = await loadCategory(slug, page);
    const canonical =
      page > 1
        ? absoluteUrl(`/categories/${cat.slug}?page=${page}`)
        : absoluteUrl(`/categories/${cat.slug}`);
    return {
      title: page > 1 ? `${cat.name} - page ${page}` : cat.name,
      description: cat.description ?? `Posts in ${cat.name}.`,
      alternates: { canonical },
      robots: cat.posts.total < 3 ? "noindex, follow" : undefined,
    };
  } catch {
    return { title: "Category" };
  }
}

export default async function CategoryPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const { slug } = await params;
  const page = parsePage((await searchParams).page);
  const cat = await loadCategory(slug, page);
  const totalPages = Math.max(1, Math.ceil(cat.posts.total / PAGE_SIZE));

  return (
    <>
      {jsonLdScript(
        breadcrumbsJsonLd([
          { name: "Home", path: "/" },
          { name: cat.name, path: `/categories/${cat.slug}` },
        ]),
      )}
      <main className="mx-auto w-full max-w-6xl px-6 py-12">
        <header>
          <p className="text-xs uppercase tracking-wider text-fg-subtle">Category</p>
          <h1 className="mt-1 font-serif text-4xl">{cat.name}</h1>
          {cat.description && (
            <p className="mt-2 max-w-prose text-fg-muted">{cat.description}</p>
          )}
          {totalPages > 1 && (
            <p className="mt-2 text-sm text-fg-muted">
              Page {page} of {totalPages}
            </p>
          )}
        </header>
        <div className="mt-8 max-w-3xl">
          {cat.posts.items.length === 0 ? (
            <p className="text-fg-muted">
              {page === 1
                ? "No posts in this category yet."
                : "Nothing on this page."}
            </p>
          ) : (
            cat.posts.items.map((p) => <PostCard key={p.slug} post={p} />)
          )}
          <Pagination
            page={page}
            totalPages={totalPages}
            basePath={`/categories/${cat.slug}`}
          />
        </div>
      </main>
    </>
  );
}
