"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { callApi, ClientApiError } from "@/lib/client-api";
import type { CommentPublic } from "@/lib/types";

interface Props {
  postSlug: string;
}

function fmt(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function Comments({ postSlug }: Props) {
  const [comments, setComments] = useState<CommentPublic[] | null>(null);
  const [replyTo, setReplyTo] = useState<{ id: string; name: string } | null>(null);
  const startedAt = useRef(Date.now());

  useEffect(() => {
    let cancelled = false;
    callApi<CommentPublic[]>(`/v1/public/posts/${postSlug}/comments`)
      .then((rows) => {
        if (!cancelled) setComments(rows);
      })
      .catch(() => {
        if (!cancelled) setComments([]);
      });
    return () => {
      cancelled = true;
    };
  }, [postSlug]);

  const { topLevel, repliesByParent } = useMemo(() => {
    const tl: CommentPublic[] = [];
    const r: Record<string, CommentPublic[]> = {};
    for (const c of comments ?? []) {
      if (c.parent_id) {
        (r[c.parent_id] = r[c.parent_id] ?? []).push(c);
      } else {
        tl.push(c);
      }
    }
    return { topLevel: tl, repliesByParent: r };
  }, [comments]);

  return (
    <section className="mt-16 border-t border-border pt-8">
      <h2 className="font-serif text-xl">Comments</h2>

      <div className="mt-6 space-y-6">
        {comments === null && (
          <p className="text-sm text-fg-muted">Loading comments…</p>
        )}
        {comments && comments.length === 0 && (
          <p className="text-sm text-fg-muted">Be the first to comment.</p>
        )}
        {topLevel.map((c) => (
          <article key={c.id}>
            <CommentRow
              comment={c}
              onReply={() => setReplyTo({ id: c.id, name: c.author_name })}
            />
            {(repliesByParent[c.id] ?? []).map((r) => (
              <div key={r.id} className="mt-4 ml-6 border-l-2 border-border pl-4">
                <CommentRow comment={r} onReply={null} />
              </div>
            ))}
          </article>
        ))}
      </div>

      <CommentForm
        postSlug={postSlug}
        startedAt={startedAt}
        replyTo={replyTo}
        onClearReply={() => setReplyTo(null)}
        onSubmitted={() => {
          // The new comment goes into moderation - show a confirmation, don't refetch.
        }}
      />
    </section>
  );
}

function CommentRow({
  comment,
  onReply,
}: {
  comment: CommentPublic;
  onReply: (() => void) | null;
}) {
  return (
    <div>
      <header className="text-sm">
        <strong>{comment.author_name}</strong>{" "}
        <span className="text-xs text-fg-subtle">{fmt(comment.created_at)}</span>
      </header>
      <p className="mt-1 whitespace-pre-wrap text-fg">{comment.content}</p>
      {onReply && (
        <button
          type="button"
          onClick={onReply}
          className="mt-1 text-xs text-accent hover:underline"
        >
          Reply
        </button>
      )}
    </div>
  );
}

function CommentForm({
  postSlug,
  startedAt,
  replyTo,
  onClearReply,
  onSubmitted,
}: {
  postSlug: string;
  startedAt: React.MutableRefObject<number>;
  replyTo: { id: string; name: string } | null;
  onClearReply: () => void;
  onSubmitted: () => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [content, setContent] = useState("");
  const [honey, setHoney] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const seconds = (Date.now() - startedAt.current) / 1000;
      await callApi<unknown>("/v1/public/comments", {
        method: "POST",
        body: JSON.stringify({
          post_slug: postSlug,
          author_name: name,
          author_email: email,
          content,
          parent_id: replyTo?.id ?? null,
          honeypot: honey || null,
          form_fill_seconds: seconds,
        }),
      });
      setDone(true);
      setName("");
      setEmail("");
      setContent("");
      onClearReply();
      onSubmitted();
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Could not submit.");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <p className="mt-8 rounded-md border border-border bg-bg-elevated p-4 text-sm text-fg-muted">
        Thanks - your comment is in moderation. It will appear once approved.
      </p>
    );
  }

  const input =
    "w-full rounded-md border border-border bg-bg px-3 py-2 text-sm focus:border-accent focus:outline-none";

  return (
    <form onSubmit={onSubmit} className="mt-10 space-y-3">
      <h3 className="font-serif text-lg">Leave a comment</h3>
      {replyTo && (
        <p className="text-xs text-fg-muted">
          Replying to <strong>{replyTo.name}</strong>{" "}
          <button
            type="button"
            onClick={onClearReply}
            className="ml-2 text-accent hover:underline"
          >
            cancel
          </button>
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          required
          minLength={1}
          maxLength={120}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name"
          autoComplete="name"
          className={input}
        />
        <input
          required
          type="email"
          maxLength={200}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email (not displayed)"
          autoComplete="email"
          className={input}
        />
      </div>
      <textarea
        required
        minLength={1}
        maxLength={5000}
        rows={4}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Your comment"
        className={input}
      />
      {/* Honeypot - visually hidden, autocomplete off; bots fill it. */}
      <input
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        value={honey}
        onChange={(e) => setHoney(e.target.value)}
        name="website"
        className="absolute -left-[10000px] h-0 w-0 opacity-0"
      />
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-fg disabled:opacity-60"
      >
        {submitting ? "Submitting…" : "Submit"}
      </button>
    </form>
  );
}
