/**
 * Typed JSON-LD builders. Each function returns the literal object that goes
 * into a <script type="application/ld+json"> tag. Centralising here means
 * schema changes can't drift from page to page.
 */
import { cloudinaryUrl } from "@/lib/cloudinary";
import { SITE_AUTHOR, SITE_NAME, SITE_URL, absoluteUrl, postUrl } from "@/lib/site";
import type { PublicPostDetail } from "@/lib/types";

/** Rough word count from rendered HTML - strip tags, count whitespace runs. */
function countWords(html: string): number {
  const text = html
    .replace(/<[^>]+>/g, " ")
    .replace(/&[a-z#0-9]+;/gi, " ")
    .trim();
  return text ? text.split(/\s+/).length : 0;
}

export function websiteJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: SITE_NAME,
    url: SITE_URL,
    potentialAction: {
      "@type": "SearchAction",
      target: `${SITE_URL}/search?q={search_term_string}`,
      "query-input": "required name=search_term_string",
    },
  };
}

export function organizationJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: SITE_NAME,
    url: SITE_URL,
  };
}

export function breadcrumbsJsonLd(crumbs: { name: string; path: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: crumbs.map((c, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: c.name,
      item: absoluteUrl(c.path),
    })),
  };
}

export function articleJsonLd(post: PublicPostDetail) {
  // Google recommends multiple aspect ratios for the article image.
  const image = post.cover
    ? (
        [
          [1200, 630],
          [1200, 900],
          [1200, 1200],
        ] as const
      ).map(([w, h]) =>
        cloudinaryUrl(post.cover!.cloudinary_public_id, {
          width: w,
          height: h,
          fit: "fill",
          cloudName: post.cover!.cloud_name,
        }),
      )
    : undefined;

  return {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    description: post.meta_description ?? post.excerpt ?? undefined,
    image,
    datePublished: post.published_at,
    dateModified: post.updated_at,
    inLanguage: "en",
    wordCount: countWords(post.content_html) || undefined,
    timeRequired: `PT${Math.max(1, post.reading_time_minutes)}M`,
    articleSection: post.category?.name ?? undefined,
    commentCount: post.comment_count,
    mainEntityOfPage: { "@type": "WebPage", "@id": postUrl(post.slug) },
    isPartOf: { "@type": "WebSite", "@id": SITE_URL, name: SITE_NAME },
    author: {
      "@type": "Person",
      name: post.author.display_name || SITE_AUTHOR,
    },
    publisher: {
      "@type": "Organization",
      name: SITE_NAME,
      url: SITE_URL,
    },
    keywords: post.tags.map((t) => t.name).join(", ") || undefined,
  };
}

export function jsonLdScript(data: object) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
