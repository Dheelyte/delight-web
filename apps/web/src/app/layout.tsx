import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";

import { ThemeInit } from "@/components/theme-init";
import { readTheme } from "@/lib/theme.server";
import "@/styles/globals.css";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
const SITE_NAME = process.env.NEXT_PUBLIC_SITE_NAME ?? "Delight Web";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_NAME,
    template: `%s - ${SITE_NAME}`,
  },
  description: "Long-form writing on engineering and craft.",
  openGraph: { type: "website", siteName: SITE_NAME, locale: "en_US" },
  twitter: { card: "summary_large_image" },
  alternates: {
    types: {
      "application/rss+xml": "/rss.xml",
      "application/atom+xml": "/atom.xml",
    },
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const theme = await readTheme();
  const nonce = (await headers()).get("x-csp-nonce") ?? undefined;
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <ThemeInit theme={theme} nonce={nonce} />
      </head>
      <body>{children}</body>
    </html>
  );
}
