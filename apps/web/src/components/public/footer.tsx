import Link from "next/link";

import { SITE_NAME } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-border bg-bg-muted">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-6 text-sm text-fg-muted">
        <span>© {new Date().getFullYear()} {SITE_NAME}</span>
        <nav className="flex flex-wrap items-center gap-4">
          <Link href="/rss.xml" className="hover:text-fg">RSS</Link>
          <Link href="/atom.xml" className="hover:text-fg">Atom</Link>
          <Link href="/sitemap.xml" className="hover:text-fg">Sitemap</Link>
          <Link href="/privacy" className="hover:text-fg">Privacy</Link>
          <Link href="/terms" className="hover:text-fg">Terms</Link>
        </nav>
      </div>
    </footer>
  );
}
