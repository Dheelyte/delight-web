/** Feed XML builders. RSS 2.0 + Atom 1.0. Escaping is mandatory. */
import { SITE_NAME, SITE_URL, postUrl } from "@/lib/site";
import type { PublicPostSummary } from "@/lib/types";

const FEED_DESCRIPTION = `Latest posts from ${SITE_NAME}`;

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export function rssXml(items: PublicPostSummary[]): string {
  const now = new Date().toUTCString();
  const xmlItems = items
    .map((p) => {
      const url = postUrl(p.slug);
      return `
    <item>
      <title>${esc(p.title)}</title>
      <link>${url}</link>
      <guid isPermaLink="true">${url}</guid>
      <pubDate>${new Date(p.published_at).toUTCString()}</pubDate>
      ${p.excerpt ? `<description>${esc(p.excerpt)}</description>` : ""}
      ${p.author.display_name ? `<author>noreply@local (${esc(p.author.display_name)})</author>` : ""}
      ${p.tags.map((t) => `<category>${esc(t.name)}</category>`).join("")}
    </item>`;
    })
    .join("");

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${esc(SITE_NAME)}</title>
    <link>${SITE_URL}</link>
    <description>${esc(FEED_DESCRIPTION)}</description>
    <language>en</language>
    <lastBuildDate>${now}</lastBuildDate>
    <atom:link href="${SITE_URL}/rss.xml" rel="self" type="application/rss+xml"/>${xmlItems}
  </channel>
</rss>`;
}

export function atomXml(items: PublicPostSummary[]): string {
  const updated = items[0]
    ? new Date(items[0].published_at).toISOString()
    : new Date().toISOString();
  const xmlItems = items
    .map((p) => {
      const url = postUrl(p.slug);
      return `
  <entry>
    <id>${url}</id>
    <title>${esc(p.title)}</title>
    <link href="${url}"/>
    <updated>${new Date(p.published_at).toISOString()}</updated>
    <published>${new Date(p.published_at).toISOString()}</published>
    <author><name>${esc(p.author.display_name)}</name></author>
    ${p.excerpt ? `<summary>${esc(p.excerpt)}</summary>` : ""}
    ${p.tags.map((t) => `<category term="${esc(t.slug)}" label="${esc(t.name)}"/>`).join("")}
  </entry>`;
    })
    .join("");

  return `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>${SITE_URL}/</id>
  <title>${esc(SITE_NAME)}</title>
  <subtitle>${esc(FEED_DESCRIPTION)}</subtitle>
  <link href="${SITE_URL}/atom.xml" rel="self"/>
  <link href="${SITE_URL}/"/>
  <updated>${updated}</updated>${xmlItems}
</feed>`;
}
