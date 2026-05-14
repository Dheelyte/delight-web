/**
 * Validate a `?next=` parameter before redirecting to it. Open-redirect prevention:
 * only same-origin paths starting with `/admin/` are accepted.
 */
export function safeNextPath(next: string | null | undefined, fallback = "/admin"): string {
  if (!next) return fallback;
  // Reject anything that could be parsed as a URL or protocol-relative path.
  if (next.startsWith("//") || next.startsWith("\\")) return fallback;
  if (!/^\/admin(\/|$)/.test(next)) return fallback;
  if (next.includes("\n") || next.includes("\r")) return fallback;
  return next;
}
