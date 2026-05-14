"use client";

import { useState } from "react";

import { callApi, ClientApiError } from "@/lib/client-api";
import { confirmDialog } from "@/lib/dialogs";

interface Series {
  id: string;
  slug: string;
  title: string;
  description: string | null;
}

export function SeriesManager({ initial }: { initial: Series[] }) {
  const [rows, setRows] = useState(initial);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");

  function sortByTitle(xs: Series[]): Series[] {
    return [...xs].sort((a, b) => a.title.localeCompare(b.title));
  }

  async function onAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const s = await callApi<Series>("/v1/series", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim() || null,
        }),
      });
      setRows((prev) => sortByTitle([...prev, s]));
      setTitle("");
      setDescription("");
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Failed.");
    } finally {
      setBusy(false);
    }
  }

  function startEdit(s: Series) {
    setEditingId(s.id);
    setEditTitle(s.title);
    setEditDescription(s.description ?? "");
  }

  async function onSaveEdit(id: string) {
    if (!editTitle.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const s = await callApi<Series>(`/v1/series/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: editTitle.trim(),
          description: editDescription.trim() || null,
        }),
      });
      setRows((prev) => sortByTitle(prev.map((x) => (x.id === id ? s : x))));
      setEditingId(null);
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(s: Series) {
    const ok = await confirmDialog({
      title: "Delete series",
      message: `"${s.title}" will be removed. This fails if any post is still in the series.`,
      confirmLabel: "Delete",
      tone: "danger",
    });
    if (!ok) return;
    setBusy(true);
    setError(null);
    try {
      await callApi<null>(`/v1/series/${s.id}`, { method: "DELETE" });
      setRows((prev) => prev.filter((x) => x.id !== s.id));
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Delete failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <form
        onSubmit={onAdd}
        className="space-y-2 rounded-lg border border-border bg-bg-elevated p-4"
      >
        <div className="flex gap-2">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Series title"
            className="flex-1 rounded-md border border-border bg-bg px-3 py-1.5 text-sm focus:border-accent focus:outline-none"
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg disabled:opacity-60"
          >
            Add
          </button>
        </div>
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description (optional)"
          className="w-full rounded-md border border-border bg-bg px-3 py-1.5 text-sm focus:border-accent focus:outline-none"
        />
      </form>
      {error && <p role="alert" className="text-xs text-red-600">{error}</p>}

      <ul className="divide-y divide-border rounded-lg border border-border bg-bg-elevated">
        {rows.length === 0 && (
          <li className="px-4 py-6 text-sm text-fg-muted">No series yet.</li>
        )}
        {rows.map((s) => (
          <li key={s.id} className="px-4 py-3 text-sm">
            {editingId === s.id ? (
              <div className="space-y-2">
                <input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="w-full rounded-md border border-border bg-bg px-2 py-1 text-sm focus:border-accent focus:outline-none"
                  autoFocus
                />
                <input
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  placeholder="Description (optional)"
                  className="w-full rounded-md border border-border bg-bg px-2 py-1 text-sm focus:border-accent focus:outline-none"
                />
                <div className="flex gap-1 text-xs">
                  <button
                    type="button"
                    onClick={() => onSaveEdit(s.id)}
                    disabled={busy}
                    className="rounded-md bg-accent px-2 py-1 font-medium text-accent-fg disabled:opacity-60"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingId(null)}
                    className="rounded-md border border-border px-2 py-1 text-fg-muted hover:bg-bg-muted"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="font-medium">{s.title}</div>
                  <div className="text-xs text-fg-subtle">{s.slug}</div>
                  {s.description && (
                    <p className="mt-1 text-xs text-fg-muted">{s.description}</p>
                  )}
                </div>
                <div className="flex gap-1 text-xs">
                  <button
                    type="button"
                    onClick={() => startEdit(s)}
                    className="rounded-md border border-border px-2 py-1 text-fg-muted hover:bg-bg-muted"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(s)}
                    disabled={busy}
                    className="rounded-md border border-border px-2 py-1 text-red-600 hover:bg-bg-muted disabled:opacity-60"
                  >
                    Delete
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
      <p className="text-xs text-fg-subtle">
        Series with attached posts cannot be deleted - detach them in the post editor first.
      </p>
    </div>
  );
}
