import Link from "next/link";

import { BlogImage } from "@/components/public/blog-image";
import { fmtDate } from "@/lib/site";
import type { PublicPostSummary } from "@/lib/types";

export function PostCard({ post, headlineLevel = 2 }: { post: PublicPostSummary; headlineLevel?: 2 | 3 }) {
  const Heading: keyof React.JSX.IntrinsicElements = `h${headlineLevel}`;
  return (
    <article className="grid gap-4 border-b border-border py-6 last:border-b-0 sm:grid-cols-[1fr_140px]">
      <div>
      <div className="text-xs text-fg-subtle">
        <time dateTime={post.published_at}>{fmtDate(post.published_at)}</time>
        <span> · {post.reading_time_minutes} min read</span>
      </div>
      <Heading className="mt-1 font-serif text-2xl leading-snug">
        <Link href={`/posts/${post.slug}`} className="hover:underline">
          {post.title}
        </Link>
      </Heading>
      {post.excerpt && <p className="mt-2 text-fg-muted">{post.excerpt}</p>}
      {post.tags.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-1 text-xs">
          {post.tags.map((t) => (
            <li key={t.slug}>
              <Link
                href={`/tags/${t.slug}`}
                className="rounded-full border border-border px-2 py-0.5 text-fg-muted hover:bg-bg-muted"
              >
                {t.name}
              </Link>
            </li>
          ))}
        </ul>
      )}
      </div>
      {post.cover && (
        <Link
          href={`/posts/${post.slug}`}
          className="hidden self-start sm:block"
          aria-hidden
          tabIndex={-1}
        >
          <BlogImage
            publicId={post.cover.cloudinary_public_id}
            cloudName={post.cover.cloud_name}
            alt=""
            width={post.cover.width}
            height={post.cover.height}
            focalX={post.cover.focal_x}
            focalY={post.cover.focal_y}
            placeholder={post.cover.placeholder_data_url}
            fit="fill"
            className="aspect-[4/3] rounded-md object-cover"
            sizes="140px"
          />
        </Link>
      )}
    </article>
  );
}
