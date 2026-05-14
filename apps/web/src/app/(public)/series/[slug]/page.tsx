import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";

import { PublicApiError, publicFetch } from "@/lib/public-api";
import { breadcrumbsJsonLd, jsonLdScript } from "@/lib/seo/jsonld";
import { fmtDate } from "@/lib/site";
import type { SeriesDetailOut, SlugRedirectOut } from "@/lib/types";

export const revalidate = 60;

async function loadSeries(slug: string): Promise<SeriesDetailOut> {
  try {
    return await publicFetch<SeriesDetailOut>(`/v1/public/series/${slug}`);
  } catch (err) {
    if (err instanceof PublicApiError && err.status === 404) {
      try {
        const r = await publicFetch<SlugRedirectOut>(
          `/v1/public/slug-history/series/${slug}`,
          { revalidate: 3600 },
        );
        permanentRedirect(`/series/${r.new_slug}`);
      } catch (lookupErr) {
        if (lookupErr instanceof PublicApiError && lookupErr.status === 404) notFound();
        throw lookupErr;
      }
    }
    throw err;
  }
}

export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> },
): Promise<Metadata> {
  const { slug } = await params;
  try {
    const s = await loadSeries(slug);
    return { title: s.title, description: s.description ?? undefined };
  } catch {
    return { title: "Series" };
  }
}

export default async function SeriesPage(
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params;
  const series = await loadSeries(slug);

  return (
    <>
      {jsonLdScript(
        breadcrumbsJsonLd([
          { name: "Home", path: "/" },
          { name: series.title, path: `/series/${series.slug}` },
        ]),
      )}
      <main className="mx-auto w-full max-w-6xl px-6 py-12">
        <header>
          <p className="text-xs uppercase tracking-wider text-fg-subtle">Series</p>
          <h1 className="mt-1 font-serif text-4xl">{series.title}</h1>
          {series.description && (
            <p className="mt-2 text-fg-muted">{series.description}</p>
          )}
        </header>
        <ol className="mt-8 space-y-4">
          {series.posts.length === 0 && (
            <p className="text-fg-muted">No published posts in this series yet.</p>
          )}
          {series.posts.map((p, i) => (
            <li
              key={p.slug}
              className="rounded-lg border border-border bg-bg-elevated p-4"
            >
              <div className="text-xs text-fg-subtle">Part {i + 1}</div>
              <h2 className="mt-1 font-serif text-xl">
                <Link href={`/posts/${p.slug}`} className="hover:underline">
                  {p.title}
                </Link>
              </h2>
              {p.excerpt && <p className="mt-1 text-sm text-fg-muted">{p.excerpt}</p>}
              <p className="mt-2 text-xs text-fg-subtle">
                <time dateTime={p.published_at}>{fmtDate(p.published_at)}</time>
                {" · "}{p.reading_time_minutes} min read
              </p>
            </li>
          ))}
        </ol>
      </main>
    </>
  );
}
