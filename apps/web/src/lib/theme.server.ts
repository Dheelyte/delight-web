import "server-only";

import { cookies } from "next/headers";

import { DEFAULT_THEME, THEME_COOKIE, type Theme } from "@/lib/theme";

/** Read the theme cookie server-side so the root layout can set `data-theme`
 *  before paint. Anything other than the literal string "dark" resolves to the
 *  light default — including a missing cookie or a stale value (e.g., "system"
 *  from before that mode was removed). */
export async function readTheme(): Promise<Theme> {
  const c = (await cookies()).get(THEME_COOKIE)?.value;
  return c === "dark" ? "dark" : DEFAULT_THEME;
}
