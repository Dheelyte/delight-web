/** Constants and small helpers used across the public site. */

export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
export const SITE_NAME = process.env.NEXT_PUBLIC_SITE_NAME ?? "Delight Web";
export const SITE_AUTHOR = process.env.NEXT_PUBLIC_SITE_AUTHOR ?? "Delight";

export function absoluteUrl(path: string): string {
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function postUrl(slug: string): string {
  return absoluteUrl(`/posts/${slug}`);
}

export function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric",
  });
}
