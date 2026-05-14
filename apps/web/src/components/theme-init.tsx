/**
 * Server-rendered script that sets `data-theme` on <html> before first paint
 * so the page never flashes the wrong theme. The server has already resolved
 * the value from the cookie via `readTheme()`; this script makes the same
 * value visible to CSS before React hydrates.
 *
 * The `nonce` prop must match the CSP nonce set by middleware so the inline
 * script executes under our strict policy.
 */
import type { Theme } from "@/lib/theme";

export function ThemeInit({ theme, nonce }: { theme: Theme; nonce?: string }) {
  const script = `document.documentElement.setAttribute("data-theme", ${JSON.stringify(theme)});`;
  // `suppressHydrationWarning` is required: browsers strip the `nonce`
  // attribute from the DOM after CSP validation, so React's hydration check
  // sees `nonce=""` on the client and would otherwise complain. The script
  // itself has already executed correctly by then.
  return (
    <script
      suppressHydrationWarning
      nonce={nonce}
      dangerouslySetInnerHTML={{ __html: script }}
    />
  );
}
