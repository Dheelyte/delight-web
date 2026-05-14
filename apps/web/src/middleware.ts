import { NextRequest, NextResponse } from "next/server";

const SESSION_COOKIE = "session";
const IS_PROD = process.env.NODE_ENV === "production";

/**
 * Build a per-request CSP. `unsafe-inline` is only allowed in development so
 * Next's hot-reload runtime works; in production every inline `<script>` must
 * carry the nonce we inject below.
 *
 * Allowlist:
 *  - 'self' for our origin
 *  - res.cloudinary.com for images
 *  - data:/blob: for LQIP background-image data URLs + canvas previews
 */
function buildCsp(nonce: string): string {
  const scriptSrc = IS_PROD
    ? `'self' 'nonce-${nonce}' 'strict-dynamic'`
    : `'self' 'unsafe-inline' 'unsafe-eval'`;

  return [
    "default-src 'self'",
    `script-src ${scriptSrc}`,
    // Inline styles are unavoidable with Tailwind's runtime + Next's dev
    // overlay; threat model accepts this.
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https://res.cloudinary.com",
    "font-src 'self' data:",
    "connect-src 'self' https://api.cloudinary.com",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    IS_PROD ? "upgrade-insecure-requests" : "",
  ]
    .filter(Boolean)
    .join("; ");
}

function makeNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

function applySecurityHeaders(response: NextResponse, nonce: string): void {
  response.headers.set("content-security-policy", buildCsp(nonce));
  response.headers.set("x-content-type-options", "nosniff");
  response.headers.set("x-frame-options", "DENY");
  response.headers.set("referrer-policy", "strict-origin-when-cross-origin");
  response.headers.set(
    "permissions-policy",
    "camera=(), microphone=(), geolocation=(), interest-cohort=()",
  );
  if (IS_PROD) {
    response.headers.set(
      "strict-transport-security",
      "max-age=31536000; includeSubDomains; preload",
    );
  }
  // Expose the nonce to RSC so layouts can read it from `headers()` and
  // attach it to any inline <script> they emit.
  response.headers.set("x-csp-nonce", nonce);
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const nonce = makeNonce();

  // Forward the nonce to downstream routes via request headers so RSCs can
  // read it with `headers().get("x-csp-nonce")`.
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-csp-nonce", nonce);

  // /admin gating - real auth still runs in the admin layout via /auth/me.
  if (
    pathname.startsWith("/admin") &&
    !pathname.startsWith("/admin/login") &&
    !request.cookies.get(SESSION_COOKIE)?.value
  ) {
    const login = request.nextUrl.clone();
    login.pathname = "/admin/login";
    login.search = `?next=${encodeURIComponent(pathname + search)}`;
    const redirect = NextResponse.redirect(login);
    applySecurityHeaders(redirect, nonce);
    return redirect;
  }

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  applySecurityHeaders(response, nonce);
  return response;
}

export const config = {
  // Run on everything except Next internals and static asset files.
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|gif|webp|avif|svg|ico|txt|xml)$).*)",
  ],
};
