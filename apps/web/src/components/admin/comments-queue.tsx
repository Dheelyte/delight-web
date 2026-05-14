"use client";

import Link from "next/link";
import { useState } from "react";

import { callApi, ClientApiError } from "@/lib/client-api";
import type { CommentAdmin, CommentList } from "@/lib/types";

export function CommentsQueue({ initial }: { initial: CommentList }) {
  const [rows, setRows] = useState<CommentAdmin[]>(initial.items);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function moderate(
    id: string,
    action: "approve" | "spam" | "delete",
  ): Promise<void> {
    setBusy(id);
    setError(null);
    try {
      const updated = await callApi<CommentAdmin>(
        action === "delete"
          ? `/v1/comments/${id}`
          : `/v1/comments/${id}/${action}`,
        { method: action === "delete" ? "DELETE" : "POST" },
      );
      // Remove from the queue if it left the {pending, spam} set.
      setRows((prev) =>
        prev.filter(
          (r) =>
            r.id !== updated.id ||
            (updated.status !== "approved" &&
              updated.status !== "deleted"),
        ),
      );
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Action failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      {rows.length === 0 ? (
        <p className="rounded-lg border border-border bg-bg-elevated p-6 text-sm text-fg-muted">
          Nothing to moderate.
        </p>
      ) : (
        <ul className="space-y-3">
          {rows.map((c) => (
            <li
              key={c.id}
              className="rounded-lg border border-border bg-bg-elevated p-4"
            >
              <header className="flex items-start justify-between gap-3 text-sm">
                <div className="min-w-0">
                  <p className="truncate text-xs text-fg-subtle">
                    On{" "}
                    <Link
                      href={`/posts/${c.post_slug}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium text-accent hover:underline"
                    >
                      {c.post_title}
                    </Link>
                  </p>
                  <div className="mt-0.5">
                    <strong>{c.author_name}</strong>{" "}
                    <span className="text-xs text-fg-subtle">
                      {new Date(c.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
                <span
                  className={
                    "shrink-0 rounded-full border px-2 py-0.5 text-xs " +
                    (c.status === "spam"
                      ? "border-red-500 text-red-600"
                      : "border-border text-fg-muted")
                  }
                >
                  {c.status}
                </span>
              </header>
              <p className="mt-2 whitespace-pre-wrap text-sm">{c.content}</p>
              <div className="mt-3 flex gap-2 text-xs">
                <button
                  type="button"
                  onClick={() => moderate(c.id, "approve")}
                  disabled={busy === c.id}
                  className="rounded-md bg-accent px-3 py-1.5 font-medium text-accent-fg disabled:opacity-60"
                >
                  Approve
                </button>
                <button
                  type="button"
                  onClick={() => moderate(c.id, "spam")}
                  disabled={busy === c.id}
                  className="rounded-md border border-border px-3 py-1.5 hover:bg-bg-muted disabled:opacity-60"
                >
                  Spam
                </button>
                <button
                  type="button"
                  onClick={() => moderate(c.id, "delete")}
                  disabled={busy === c.id}
                  className="rounded-md border border-border px-3 py-1.5 text-red-600 hover:bg-bg-muted disabled:opacity-60"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
