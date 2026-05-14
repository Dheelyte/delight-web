import type { Metadata } from "next";

import { SITE_NAME } from "@/lib/site";

export const metadata: Metadata = { title: "About" };

export default function AboutPage() {
  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-12">
      <div className="max-w-prose">
        <h1 className="font-serif text-4xl">About</h1>
        <p className="mt-6 text-lg text-fg-muted">
          {SITE_NAME} is a personal writing space focused on engineering and craft.
        </p>
        <p className="mt-4 text-fg-muted">
          Replace this copy with your real about page — it's a CMS-managed page in
          Stage 6 once the site has real content to anchor it.
        </p>
      </div>
    </main>
  );
}
