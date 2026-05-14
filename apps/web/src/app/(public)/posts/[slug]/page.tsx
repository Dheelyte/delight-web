import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";

import { AuthorCard } from "@/components/public/author-card";
import { BlogImage, ogImageUrl } from "@/components/public/blog-image";
import { Comments } from "@/components/public/comments";
import { ReadingProgress } from "@/components/public/reading-progress";
import { ShareBar } from "@/components/public/share-bar";
import { SubscribeForm } from "@/components/public/subscribe-form";
import { ViewTracker } from "@/components/public/view-tracker";
import { addHeadingAnchors } from "@/lib/heading-anchors";
import { optimizeInlineImages } from "@/lib/inline-images";
import { PublicApiError, publicFetch } from "@/lib/public-api";
import {
  articleJsonLd,
  breadcrumbsJsonLd,
  jsonLdScript,
} from "@/lib/seo/jsonld";
import { fmtDate, postUrl, SITE_NAME } from "@/lib/site";
import type { PublicPostDetail, SlugRedirectOut } from "@/lib/types";

export const revalidate = 300;

async function loadPost(slug: string): Promise<PublicPostDetail> {
  try {
    return await publicFetch<PublicPostDetail>(`/v1/public/posts/${slug}`, {
      revalidate: 300,
    });
  } catch (err) {
    if (err instanceof PublicApiError && err.status === 404) {
      // SEO: a renamed post must 301-redirect from the old slug, never 404.
      try {
        const redir = await publicFetch<SlugRedirectOut>(
          `/v1/public/slug-history/post/${slug}`,
          { revalidate: 3600 },
        );
        permanentRedirect(`/posts/${redir.new_slug}`);
      } catch (lookupErr) {
        if (lookupErr instanceof PublicApiError && lookupErr.status === 404) {
          notFound();
        }
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
  let post: PublicPostDetail;
  try {
    post = await loadPost(slug);
  } catch {
    return { title: "Not found" };
  }
  const title = post.meta_title ?? post.title;
  const description = post.meta_description ?? post.excerpt ?? undefined;
  const canonical = post.canonical_url ?? postUrl(post.slug);
  const og = post.cover
    ? ogImageUrl(post.cover.cloudinary_public_id, post.cover.cloud_name)
    : undefined;

  return {
    title,
    description,
    alternates: { canonical },
    robots: post.robots ?? undefined,
    openGraph: {
      type: "article",
      title,
      description,
      url: canonical,
      siteName: SITE_NAME,
      publishedTime: post.published_at,
      modifiedTime: post.updated_at,
      authors: [post.author.display_name],
      tags: post.tags.map((t) => t.name),
      images: og ? [{ url: og, width: 1200, height: 630, alt: post.cover!.alt }] : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: og ? [og] : undefined,
    },
  };
}

// Only surface "Updated" when the post was meaningfully revised *after*
// publishing — same-day edits / tweaks shouldn't claim freshness.
const UPDATED_THRESHOLD_MS = 24 * 60 * 60 * 1000;

export default async function PostPage(
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params;
  const post = await loadPost(slug);

  // One pass: add heading anchors (+ collect the TOC), then rewrite inline
  // Cloudinary images onto the responsive pipeline.
  const { html: anchoredHtml, headings } = addHeadingAnchors(post.content_html);
  const bodyHtml = optimizeInlineImages(anchoredHtml);

  const showUpdated =
    new Date(post.updated_at).getTime() - new Date(post.published_at).getTime() >
    UPDATED_THRESHOLD_MS;

  const hasRail = headings.length >= 2 || post.related.length > 0;

  return (
    <>
      {jsonLdScript(articleJsonLd(post))}
      {jsonLdScript(
        breadcrumbsJsonLd([
          { name: "Home", path: "/" },
          { name: post.title, path: `/posts/${post.slug}` },
        ]),
      )}

      <ReadingProgress />

      <main className="mx-auto w-full max-w-6xl px-6 py-12">
        {/*
          Two-column layout at lg+: the article body on the left, a sticky
          related-posts rail on the right. Below lg the grid collapses to one
          column, so the rail flows after the article body naturally.
          Series nav + comments sit below as full-width sections.
        */}
        <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_16rem] lg:gap-10">
          <article id="post-article" className="min-w-0">
            {post.series && (
              <p className="mb-4 text-sm text-fg-muted">
                Part {post.series_order} of the{" "}
                <Link href={`/series/${post.series.slug}`} className="hover:underline">
                  {post.series.title}
                </Link>{" "}
                series
              </p>
            )}

            <header className="mb-5">
              <h1 className="font-serif text-4xl leading-tight md:text-5xl">{post.title}</h1>
              <p className="mt-3 text-sm text-fg-subtle">
                <time dateTime={post.published_at}>{fmtDate(post.published_at)}</time>
                {" · "}
                {post.reading_time_minutes} min read
                {" · "}
                by {post.author.display_name}
                {showUpdated && (
                  <>
                    {" · "}
                    Updated{" "}
                    <time dateTime={post.updated_at}>
                      {fmtDate(post.updated_at)}
                    </time>
                  </>
                )}
              </p>
              {post.tags.length > 0 && (
                <ul className="mt-3 flex flex-wrap gap-1 text-xs">
                  {post.tags.map((t) => (
                    <li key={t.slug}>
                      <Link
                        href={`/tags/${t.slug}`}
                        className="rounded-full border border-border px-2 py-0.5 text-fg-muted hover:bg-bg-muted"
                      >
                        {t.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </header>

            {post.cover && (
              <figure className="-mx-6 mt-8 mb-8 md:mx-0">
                <BlogImage
                  publicId={post.cover.cloudinary_public_id}
                  cloudName={post.cover.cloud_name}
                  alt={post.cover.alt}
                  width={post.cover.width}
                  height={post.cover.height}
                  focalX={post.cover.focal_x}
                  focalY={post.cover.focal_y}
                  placeholder={post.cover.placeholder_data_url}
                  priority
                  className="md:rounded-lg"
                  sizes="(min-width: 1024px) 720px, (min-width: 768px) 720px, 100vw"
                />
              </figure>
            )}

            

            <div
              className="post-prose prose mt-10 max-w-none font-serif text-lg leading-relaxed [&_h2]:mt-10 [&_h2]:font-serif [&_h2]:text-2xl [&_h3]:mt-8 [&_h3]:font-serif [&_h3]:text-xl [&_p]:my-4 [&_a]:text-accent [&_a]:underline [&_blockquote]:border-l-4 [&_blockquote]:border-border [&_blockquote]:pl-4 [&_blockquote]:italic [&_code]:rounded [&_code]:bg-bg-muted [&_code]:px-1 [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-bg-muted [&_pre]:p-4 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_img]:rounded-lg [&_ul]:my-4 [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:my-4 [&_ol]:list-decimal [&_ol]:pl-6"
              dangerouslySetInnerHTML={{ __html: bodyHtml }}
            />

            <ShareBar
              className="mt-12"
              url={post.canonical_url ?? postUrl(post.slug)}
              title={post.title}
            />

            <AuthorCard author={post.author} />

            <section className="mt-12 rounded-lg border border-border bg-bg-elevated p-6">
              <h2 className="font-serif text-lg">Enjoyed this?</h2>
              <p className="mt-1 text-sm text-fg-muted">
                Get new posts in your inbox. No spam, unsubscribe anytime.
              </p>
              <div className="mt-3 max-w-sm">
                <SubscribeForm />
              </div>
            </section>
          </article>

          {hasRail && (
            <aside className="mt-16 lg:mt-0">
              <div className="space-y-10 lg:sticky lg:top-20">

                {post.related.length > 0 && (
                  <div>
                <h2 className="font-serif text-xs font-semibold uppercase tracking-wider text-fg-subtle">
                  Related reading
                </h2>
                <ul className="mt-3 space-y-5">
                  {post.related.slice(0, 5).map((p) => (
                    <li
                      key={p.slug}
                      className="border-t border-border pt-4 first:border-t-0 first:pt-0"
                    >
                      <Link
                        href={`/posts/${p.slug}`}
                        className="group flex gap-3"
                      >
                        {p.cover && (
                          <div className="shrink-0">
                            <BlogImage
                              publicId={p.cover.cloudinary_public_id}
                              cloudName={p.cover.cloud_name}
                              alt=""
                              width={p.cover.width}
                              height={p.cover.height}
                              focalX={p.cover.focal_x}
                              focalY={p.cover.focal_y}
                              placeholder={p.cover.placeholder_data_url}
                              fit="fill"
                              className="aspect-[4/3] h-14 w-20 rounded-md"
                              sizes="80px"
                            />
                          </div>
                        )}
                        <div className="min-w-0 flex-1">
                        <h3 className="font-serif text-base leading-snug group-hover:underline">
                          {p.title}
                        </h3>
                        <p className="mt-1 text-xs text-fg-subtle">
                          <time dateTime={p.published_at}>{fmtDate(p.published_at)}</time>
                          {" · "}
                          {p.reading_time_minutes} min read
                        </p>
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
                  </div>
                )}
              </div>
            </aside>
          )}
        </div>

        <div className="mx-auto w-full max-w-3xl">
          {(post.prev_in_series || post.next_in_series) && (
            <nav className="mt-12 grid gap-4 sm:grid-cols-2">
              {post.prev_in_series && (
                <Link
                  href={`/posts/${post.prev_in_series.slug}`}
                  className="rounded-lg border border-border bg-bg-elevated p-4 hover:bg-bg-muted"
                >
                  <div className="text-xs text-fg-subtle">← Previous in series</div>
                  <div className="mt-1 font-serif text-lg">{post.prev_in_series.title}</div>
                </Link>
              )}
              {post.next_in_series && (
                <Link
                  href={`/posts/${post.next_in_series.slug}`}
                  className="rounded-lg border border-border bg-bg-elevated p-4 text-right hover:bg-bg-muted"
                >
                  <div className="text-xs text-fg-subtle">Next in series →</div>
                  <div className="mt-1 font-serif text-lg">{post.next_in_series.title}</div>
                </Link>
              )}
            </nav>
          )}

          <Comments postSlug={post.slug} />
        </div>
      </main>

      <ViewTracker postSlug={post.slug} />
    </>
  );
}

