/** Theme types + constants. Safe to import from client OR server components.
 *
 *  The server-only cookie reader lives in `theme.server.ts` so that
 *  `next/headers` never ends up in the client bundle via this module — Next's
 *  static analyser refuses to compile when a client component transitively
 *  imports `next/headers`, even via something it doesn't actually call.
 */
export type Theme = "light" | "dark";
export const THEME_COOKIE = "theme";
export const DEFAULT_THEME: Theme = "light";
