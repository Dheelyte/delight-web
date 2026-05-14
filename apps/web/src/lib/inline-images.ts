/**
 * Rewrites Cloudinary <img> tags in post HTML to use the responsive delivery
 * pipeline. CKEditor inserts bare upload URLs:
 *
 *   <img src="https://res.cloudinary.com/CLOUD/image/upload/v123/posts/inline/x.jpg">
 *
 * which serves the untouched original at full size - a real LCP and bandwidth
 * hit. This transform injects `f_auto,q_auto` (per-request AVIF/WebP + quality)
 * and a width `srcset`, plus `loading="lazy"` / `decoding="async"`:
 *
 *   <img src="…/image/upload/f_auto,q_auto,w_1200/v123/posts/inline/x.jpg"
 *        srcset="…w_400… 400w, …w_800… 800w, …" sizes="…"
 *        loading="lazy" decoding="async">
 *
 * Runs server-side on already-sanitised HTML (same place as addHeadingAnchors),
 * so the optimised markup ships in the initial response. Non-Cloudinary <img>
 * tags - e.g. pasted external URLs - are left untouched.
 */

const IMG_RE = /<img\b([^>]*)>/gi;
const SRC_RE = /\bsrc\s*=\s*"([^"]*)"/i;
const UPLOAD_MARKER = "/image/upload/";
const CLOUDINARY_HOST = "res.cloudinary.com";

const WIDTHS = [400, 800, 1200, 1600] as const;
const FALLBACK_WIDTH = 1200;
// In-article images: full viewport width on mobile, capped to the article
// column on wider screens. Matches the post-detail article column.
const SIZES = "(min-width: 768px) 720px, 100vw";

function isCloudinaryUpload(url: string): boolean {
  return url.includes(CLOUDINARY_HOST) && url.includes(UPLOAD_MARKER);
}

/**
 * Insert a transform segment right after `/image/upload/`. Cloudinary chains
 * transform segments, so this is safe even if the URL somehow already has one
 * (e.g. an image inserted via "insert by URL" with transforms baked in).
 */
function withTransform(url: string, transform: string): string {
  return url.replace(UPLOAD_MARKER, `${UPLOAD_MARKER}${transform}/`);
}

function buildSrcSet(url: string): string {
  return WIDTHS.map(
    (w) => `${withTransform(url, `f_auto,q_auto,w_${w}`)} ${w}w`,
  ).join(", ");
}

export function optimizeInlineImages(html: string): string {
  return html.replace(IMG_RE, (_tag, rawAttrs: string) => {
    // Drop a trailing self-closing slash so re-appended attrs stay well-formed.
    const attrs = rawAttrs.replace(/\s*\/\s*$/, "");
    const src = SRC_RE.exec(attrs)?.[1];

    if (!src || !isCloudinaryUpload(src)) {
      return `<img${attrs}>`;
    }

    let next = attrs.replace(
      SRC_RE,
      `src="${withTransform(src, `f_auto,q_auto,w_${FALLBACK_WIDTH}`)}"`,
    );
    // Only add attributes the editor didn't already set.
    if (!/\bsrcset\s*=/i.test(next)) next += ` srcset="${buildSrcSet(src)}"`;
    if (!/\bsizes\s*=/i.test(next)) next += ` sizes="${SIZES}"`;
    if (!/\bloading\s*=/i.test(next)) next += ` loading="lazy"`;
    if (!/\bdecoding\s*=/i.test(next)) next += ` decoding="async"`;

    return `<img${next}>`;
  });
}
