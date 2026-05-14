import type { AuthorOut } from "@/lib/types";

/**
 * End-of-article author card. Renders only when there's something beyond the
 * name to show (a bio or an avatar) - the byline already covers a bare name.
 * Part of the page's E-E-A-T signal: a clear "who wrote this".
 */
export function AuthorCard({ author }: { author: AuthorOut }) {
  if (!author.bio && !author.avatar_url) return null;

  return (
    <aside className="mt-12 flex gap-4 rounded-lg border border-border bg-bg-elevated p-5">
      {author.avatar_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={author.avatar_url}
          alt={author.display_name}
          width={56}
          height={56}
          loading="lazy"
          decoding="async"
          className="h-14 w-14 shrink-0 rounded-full object-cover"
        />
      )}
      <div className="min-w-0">
        <p className="text-xs uppercase tracking-wider text-fg-subtle">
          Written by
        </p>
        <p className="font-serif text-lg">{author.display_name}</p>
        {author.bio && (
          <p className="mt-1 text-sm leading-relaxed text-fg-muted">
            {author.bio}
          </p>
        )}
      </div>
    </aside>
  );
}
