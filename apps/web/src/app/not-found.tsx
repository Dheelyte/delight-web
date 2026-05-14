import Link from "next/link";

export default function NotFound() {
  return (
    <main className="grid min-h-dvh place-items-center bg-bg px-6 text-center">
      <div>
        <p className="font-mono text-sm text-fg-subtle">404</p>
        <h1 className="mt-2 font-serif text-4xl">Nothing here</h1>
        <p className="mt-3 max-w-md text-fg-muted">
          The page you're looking for doesn't exist - or has moved and the
          redirect has lapsed.
        </p>
        <Link
          href="/"
          className="mt-6 inline-block rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-fg"
        >
          Back to home
        </Link>
      </div>
    </main>
  );
}
