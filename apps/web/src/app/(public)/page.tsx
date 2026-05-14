import Link from "next/link";

import { Pagination, parsePage } from "@/components/pagination";
import { BlogImage } from "@/components/public/blog-image";
import { PostCard } from "@/components/public/post-card";
import { SubscribeForm } from "@/components/public/subscribe-form";
import { publicFetch } from "@/lib/public-api";
import { jsonLdScript, organizationJsonLd, websiteJsonLd } from "@/lib/seo/jsonld";
import { fmtDate } from "@/lib/site";
import type { PublicPostList } from "@/lib/types";

export const revalidate = 60;

const PAGE_SIZE = 10;

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const page = parsePage((await searchParams).page);
  const offset = (page - 1) * PAGE_SIZE;
  const data = await publicFetch<PublicPostList>(
    `/v1/public/posts?limit=${PAGE_SIZE}&offset=${offset}`,
  );
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  // The "Featured" hero treatment is page-1 only; later pages are a plain feed.
  const showHero = page === 1 && data.items.length > 0;
  const hero = showHero ? data.items[0] : null;
  const feed = showHero ? data.items.slice(1) : data.items;

  return (
    <>
      {jsonLdScript(websiteJsonLd())}
      {jsonLdScript(organizationJsonLd())}

      <main className="mx-auto w-full max-w-6xl px-6 py-12">
        {data.items.length === 0 ? (
          <p className="text-fg-muted">
            {page === 1
              ? "No posts yet - check back soon."
              : "Nothing on this page."}
          </p>
        ) : (
          <>
            {hero && (
              <article className="grid gap-6 border-b border-border pb-12 md:grid-cols-2 md:items-center">
                {hero.cover && (
                  <Link href={`/posts/${hero.slug}`} className="block">
                    <BlogImage
                      publicId={hero.cover.cloudinary_public_id}
                      cloudName={hero.cover.cloud_name}
                      alt={hero.cover.alt}
                      width={hero.cover.width}
                      height={hero.cover.height}
                      focalX={hero.cover.focal_x}
                      focalY={hero.cover.focal_y}
                      placeholder={hero.cover.placeholder_data_url}
                      fit="fill"
                      priority
                      className="aspect-[4/3] rounded-lg object-cover"
                      sizes="(min-width: 768px) 480px, 100vw"
                    />
                  </Link>
                )}
                <div>
                  <div className="text-xs uppercase tracking-wider text-fg-subtle">
                    Featured
                  </div>
                  <h1 className="mt-2 font-serif text-4xl leading-tight md:text-5xl">
                    <Link href={`/posts/${hero.slug}`} className="hover:underline">
                      {hero.title}
                    </Link>
                  </h1>
                  {hero.excerpt && (
                    <p className="mt-4 max-w-prose text-lg text-fg-muted">
                      {hero.excerpt}
                    </p>
                  )}
                  <p className="mt-3 text-xs text-fg-subtle">
                    <time dateTime={hero.published_at}>
                      {fmtDate(hero.published_at)}
                    </time>
                    {" · "}
                    {hero.reading_time_minutes} min read
                  </p>
                </div>
              </article>
            )}

            <section className="mt-10 grid gap-10 lg:grid-cols-3">
              <div className="lg:col-span-2">
                {feed.length > 0 ? (
                  feed.map((p) => <PostCard key={p.slug} post={p} />)
                ) : (
                  <p className="text-fg-muted">That's everything for now.</p>
                )}
                <Pagination page={page} totalPages={totalPages} basePath="/" />
              </div>
              <aside className="space-y-6 text-sm">
                <div className="rounded-lg border border-border bg-bg-elevated p-4">
                  <h2 className="font-serif text-lg">About</h2>
                  <p className="mt-2 text-fg-muted">
                    Long-form writing on engineering and craft.
                  </p>
                  <Link
                    href="/about"
                    className="mt-3 inline-block text-accent hover:underline"
                  >
                    Read more →
                  </Link>
                </div>
                <div className="rounded-lg border border-border bg-bg-elevated p-4">
                  <h2 className="font-serif text-lg">Subscribe</h2>
                  <p className="mt-2 text-fg-muted">
                    Get new posts in your inbox. Double opt-in; unsubscribe anytime.
                  </p>
                  <div className="mt-3">
                    <SubscribeForm />
                  </div>
                  <div className="mt-3 flex gap-3 text-xs text-fg-subtle">
                    <Link href="/rss.xml" className="hover:underline">
                      RSS
                    </Link>
                    <Link href="/atom.xml" className="hover:underline">
                      Atom
                    </Link>
                  </div>
                </div>
              </aside>
            </section>
          </>
        )}
      </main>
    </>
  );
}
