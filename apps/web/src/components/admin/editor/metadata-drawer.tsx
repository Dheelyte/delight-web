"use client";

import { useEffect, useState } from "react";

import { CoverPicker } from "./cover-picker";
import { callApi, ClientApiError } from "@/lib/client-api";
import type { PostDetail, SlugCheck, Tag } from "@/lib/types";

interface Props {
  post: PostDetail;
  allTags: Tag[];
  onSaved: (updated: PostDetail) => void;
}

export function MetadataDrawer({ post, allTags, onSaved }: Props) {
  const [slug, setSlug] = useState(post.slug);
  const [excerpt, setExcerpt] = useState(post.excerpt ?? "");
  const [coverImageId, setCoverImageId] = useState<string | null>(post.cover_image_id);
  const [tagIds, setTagIds] = useState<string[]>(post.tag_ids);
  const [metaTitle, setMetaTitle] = useState(post.meta_title ?? "");
  const [metaDescription, setMetaDescription] = useState(post.meta_description ?? "");
  const [slugStatus, setSlugStatus] = useState<"idle" | "checking" | "ok" | "taken">("idle");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Debounced slug availability check.
  useEffect(() => {
    if (slug === post.slug) {
      setSlugStatus("idle");
      return;
    }
    if (!/^[a-z0-9-]+$/.test(slug)) {
      setSlugStatus("taken");
      return;
    }
    setSlugStatus("checking");
    const handle = setTimeout(async () => {
      try {
        const data = await callApi<SlugCheck>(
          `/v1/posts/check-slug?slug=${encodeURIComponent(slug)}&exclude_post_id=${post.id}`,
        );
        setSlugStatus(data.available ? "ok" : "taken");
      } catch {
        setSlugStatus("idle");
      }
    }, 350);
    return () => clearTimeout(handle);
  }, [slug, post.slug, post.id]);

  async function saveMetadata() {
    setSaving(true);
    setError(null);
    try {
      const updated = await callApi<PostDetail>(`/v1/posts/${post.id}/metadata`, {
        method: "PUT",
        body: JSON.stringify({
          slug,
          tag_ids: tagIds,
          meta_title: metaTitle || null,
          meta_description: metaDescription || null,
          canonical_url: null,
          robots: null,
          cover_image_id: coverImageId,
          category_id: post.category_id,
          series_id: post.series_id,
          series_order: post.series_order,
        }),
      });
      onSaved(updated);
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  function toggleTag(id: string) {
    setTagIds((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]));
  }

  return (
    <aside className="w-80 shrink-0 space-y-5 border-l border-border bg-bg-elevated p-5 text-sm">
      <Field label="Slug" hint={slugHint(slugStatus)}>
        <input
          value={slug}
          onChange={(e) => setSlug(e.target.value.toLowerCase())}
          className={input}
        />
      </Field>

      <Field label="Excerpt">
        <textarea
          value={excerpt}
          onChange={(e) => setExcerpt(e.target.value)}
          rows={3}
          className={input}
        />
      </Field>

      <Field label="Cover image">
        <CoverPicker initialMediaId={coverImageId} onChange={setCoverImageId} />
      </Field>

      <Field label="Tags">
        <div className="flex flex-wrap gap-1">
          {allTags.length === 0 && (
            <span className="text-xs text-fg-subtle">No tags yet.</span>
          )}
          {allTags.map((t) => {
            const on = tagIds.includes(t.id);
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => toggleTag(t.id)}
                className={
                  "rounded-full border px-2 py-0.5 text-xs " +
                  (on
                    ? "border-accent bg-accent text-accent-fg"
                    : "border-border text-fg-muted hover:bg-bg-muted")
                }
              >
                {t.name}
              </button>
            );
          })}
        </div>
      </Field>

      <Field label="SEO title (≤60)">
        <input
          value={metaTitle}
          onChange={(e) => setMetaTitle(e.target.value)}
          maxLength={60}
          className={input}
        />
      </Field>
      <Field label="SEO description (≤155)">
        <textarea
          value={metaDescription}
          onChange={(e) => setMetaDescription(e.target.value)}
          maxLength={155}
          rows={2}
          className={input}
        />
      </Field>

      {error && (
        <p role="alert" className="text-xs text-red-600">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={saveMetadata}
        disabled={saving || slugStatus === "taken" || slugStatus === "checking"}
        className="w-full rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-fg disabled:opacity-60"
      >
        {saving ? "Saving…" : "Save metadata"}
      </button>
    </aside>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <label className="text-xs font-medium text-fg-muted">{label}</label>
        {hint && <span className="text-[10px] text-fg-subtle">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

const input =
  "w-full rounded-md border border-border bg-bg px-2 py-1.5 text-sm " +
  "focus:border-accent focus:outline-none";

function slugHint(s: "idle" | "checking" | "ok" | "taken"): string | undefined {
  if (s === "checking") return "checking…";
  if (s === "ok") return "available";
  if (s === "taken") return "taken / invalid";
  return undefined;
}

