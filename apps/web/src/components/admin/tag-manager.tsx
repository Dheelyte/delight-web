"use client";

import { useState } from "react";

import { callApi, ClientApiError } from "@/lib/client-api";
import { confirmDialog } from "@/lib/dialogs";
import type { Tag } from "@/lib/types";

export function TagManager({ initialTags }: { initialTags: Tag[] }) {
  const [tags, setTags] = useState(initialTags);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");

  function sortByName(rows: Tag[]): Tag[] {
    return [...rows].sort((a, b) => a.name.localeCompare(b.name));
  }

  async function onAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const t = await callApi<Tag>("/v1/tags", {
        method: "POST",
        body: JSON.stringify({ name: name.trim() }),
      });
      setTags((prev) => sortByName([...prev, t]));
      setName("");
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Failed.");
    } finally {
      setBusy(false);
    }
  }

  async function onSaveEdit(id: string) {
    const trimmed = editingName.trim();
    if (!trimmed) return;
    setBusy(true);
    setError(null);
    try {
      const t = await callApi<Tag>(`/v1/tags/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ name: trimmed }),
      });
      setTags((prev) => sortByName(prev.map((x) => (x.id === id ? t : x))));
      setEditingId(null);
      setEditingName("");
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(t: Tag) {
    const ok = await confirmDialog({
      title: "Delete tag",
      message: `"${t.name}" will be removed. This fails if the tag is still attached to any post.`,
      confirmLabel: "Delete",
      tone: "danger",
    });
    if (!ok) return;
    setBusy(true);
    setError(null);
    try {
      await callApi<null>(`/v1/tags/${t.id}`, { method: "DELETE" });
      setTags((prev) => prev.filter((x) => x.id !== t.id));
    } catch (err) {
      setError(
        err instanceof ClientApiError
          ? err.message
          : "Delete failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={onAdd} className="flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New tag name"
          className="flex-1 rounded-md border border-border bg-bg px-3 py-1.5 text-sm focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg disabled:opacity-60"
        >
          Add
        </button>
      </form>
      {error && <p role="alert" className="text-xs text-red-600">{error}</p>}

      <ul className="divide-y divide-border rounded-lg border border-border bg-bg-elevated">
        {tags.length === 0 && (
          <li className="px-4 py-6 text-sm text-fg-muted">No tags yet.</li>
        )}
        {tags.map((t) => (
          <li key={t.id} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
            {editingId === t.id ? (
              <>
                <input
                  value={editingName}
                  onChange={(e) => setEditingName(e.target.value)}
                  className="flex-1 rounded-md border border-border bg-bg px-2 py-1 text-sm focus:border-accent focus:outline-none"
                  autoFocus
                />
                <div className="flex gap-1 text-xs">
                  <button
                    type="button"
                    onClick={() => onSaveEdit(t.id)}
                    disabled={busy}
                    className="rounded-md bg-accent px-2 py-1 font-medium text-accent-fg disabled:opacity-60"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEditingId(null);
                      setEditingName("");
                    }}
                    className="rounded-md border border-border px-2 py-1 text-fg-muted hover:bg-bg-muted"
                  >
                    Cancel
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="min-w-0 flex-1">
                  <div className="truncate">{t.name}</div>
                  <div className="text-xs text-fg-subtle">{t.slug}</div>
                </div>
                <div className="flex gap-1 text-xs">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingId(t.id);
                      setEditingName(t.name);
                    }}
                    className="rounded-md border border-border px-2 py-1 text-fg-muted hover:bg-bg-muted"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(t)}
                    disabled={busy}
                    className="rounded-md border border-border px-2 py-1 text-red-600 hover:bg-bg-muted disabled:opacity-60"
                  >
                    Delete
                  </button>
                </div>
              </>
            )}
          </li>
        ))}
      </ul>
      <p className="text-xs text-fg-subtle">
        Tags in use by a post cannot be deleted - remove them from the posts first.
      </p>
    </div>
  );
}
