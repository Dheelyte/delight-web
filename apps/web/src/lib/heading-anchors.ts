/**
 * Rewrites <h2>/<h3> in post HTML into self-linking section anchors:
 *
 *   <h2 id="this-is-a-section">
 *     <a class="heading-anchor" href="#this-is-a-section">…original inner HTML…</a>
 *   </h2>
 *
 * Runs server-side on already-sanitised HTML, so the `id`s ship in the served
 * markup - native `#fragment` navigation works on first load without any JS,
 * and the whole heading is a click target that updates the URL hash.
 *
 * The slug comes from the heading's *text* content (inline markup stripped).
 * Duplicate slugs within one document get a numeric suffix so every id is
 * unique and stable for a given document.
 */

// Common named entities CKEditor / PasteFromOffice emit. We decode to the
// *real* character so slugify treats it correctly - e.g. `&nbsp;` must become
// a space, not the literal letters "nbsp". Anything not in this map falls
// through to the catch-all below and is replaced with a space.
const NAMED_ENTITIES: Record<string, string> = {
  nbsp: " ",
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
  mdash: "-",
  ndash: "–",
  hellip: "…",
  lsquo: "‘",
  rsquo: "’",
  ldquo: "“",
  rdquo: "”",
};

function safeFromCodePoint(cp: number): string {
  try {
    return Number.isFinite(cp) && cp >= 0 && cp <= 0x10ffff
      ? String.fromCodePoint(cp)
      : " ";
  } catch {
    return " ";
  }
}

/**
 * Decode HTML entities in a plain-text fragment. `content_html` is a raw
 * string, so entities arrive un-decoded (`&nbsp;`, `&amp;`, `&#39;`, …) and
 * would otherwise leak their *names* into slugs.
 */
function decodeEntities(text: string): string {
  return text
    .replace(/&#x([0-9a-f]+);/gi, (_m, hex: string) =>
      safeFromCodePoint(parseInt(hex, 16)),
    )
    .replace(/&#(\d+);/g, (_m, dec: string) =>
      safeFromCodePoint(parseInt(dec, 10)),
    )
    .replace(/&([a-z][a-z0-9]*);/gi, (_m, name: string) => {
      // Known non-letter entity → its char; anything else → space so the
      // entity name can't survive into the slug.
      return NAMED_ENTITIES[name.toLowerCase()] ?? " ";
    });
}

function slugify(text: string): string {
  const slug = decodeEntities(text)
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "") // strip combining diacritics
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80)
    .replace(/-+$/g, ""); // re-trim in case the slice landed on a hyphen
  return slug || "section";
}

// `<h2>` / `<h3>`, tolerating (and discarding) any attributes the sanitiser
// might one day let through. Headings can't nest, so the non-greedy body
// match is safe.
const HEADING_RE = /<h([23])(?:\s[^>]*)?>([\s\S]*?)<\/h\1>/g;
const TAG_RE = /<[^>]+>/g;

/** One entry in a post's table of contents. */
export interface TocHeading {
  level: 2 | 3;
  /** Plain text (inline markup stripped, entities decoded) for display. */
  text: string;
  /** The id assigned to the heading - also the `#fragment` target. */
  slug: string;
}

export interface HeadingAnchorResult {
  /** The post HTML with self-linking, id-bearing headings. */
  html: string;
  /** Ordered h2/h3 list for rendering a table of contents. */
  headings: TocHeading[];
}

export function addHeadingAnchors(html: string): HeadingAnchorResult {
  const seen = new Map<string, number>();
  const headings: TocHeading[] = [];

  const out = html.replace(
    HEADING_RE,
    (_match, level: string, inner: string) => {
      // Strip inline tags; `slugify` then decodes entities and trims edge
      // hyphens, so a literal trailing `&nbsp;` no longer leaks into the slug.
      const rawText = inner.replace(TAG_RE, "");
      const base = slugify(rawText);
      const used = seen.get(base) ?? 0;
      seen.set(base, used + 1);
      const slug = used === 0 ? base : `${base}-${used + 1}`;

      headings.push({
        level: level === "3" ? 3 : 2,
        text: decodeEntities(rawText).replace(/\s+/g, " ").trim(),
        slug,
      });

      return (
        `<h${level} id="${slug}">` +
        `<a class="heading-anchor" href="#${slug}">${inner}</a>` +
        `</h${level}>`
      );
    },
  );

  return { html: out, headings };
}
