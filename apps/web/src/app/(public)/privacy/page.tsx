import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy" };

export default function PrivacyPage() {
  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-12">
      <div className="max-w-prose">
        <h1 className="font-serif text-4xl">Privacy</h1>
        <p className="mt-6 text-fg-muted">
          Page views are recorded with a hashed session identifier — no personal
          data is stored. Newsletter subscriptions store only your email, with
          double opt-in, and you can unsubscribe via the signed link at the
          bottom of every email.
        </p>
      </div>
    </main>
  );
}
