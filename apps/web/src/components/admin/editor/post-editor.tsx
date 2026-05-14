"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { MetadataDrawer } from "./metadata-drawer";
import { RichEditor, type RichEditorHandle } from "./rich-editor";
import { callApi, ClientApiError } from "@/lib/client-api";
import { confirmDialog } from "@/lib/dialogs";
import type { PostDetail, Tag } from "@/lib/types";

const AUTOSAVE_INTERVAL_MS = 5000;

type SaveState =
  | { kind: "clean"; savedAt: Date | null }
  | { kind: "dirty" }
  | { kind: "saving" }
  | { kind: "error"; message: string };

export function PostEditor({
  initialPost,
  allTags,
}: {
  initialPost: PostDetail;
  allTags: Tag[];
}) {
  const router = useRouter();
  const [post, setPost] = useState(initialPost);
  const [title, setTitle] = useState(initialPost.title);
  const editorRef = useRef<RichEditorHandle>(null);
  const dirtyRef = useRef(false);
  const [state, setState] = useState<SaveState>({ kind: "clean", savedAt: null });

  const persist = useCallback(
    async (autosave: boolean) => {
      const html = editorRef.current?.getHtml() ?? "";
      setState({ kind: "saving" });
      try {
        const updated = await callApi<PostDetail>(`/v1/posts/${post.id}/content`, {
          method: "PUT",
          body: JSON.stringify({
            title: title.trim() || "Untitled",
            excerpt: post.excerpt,
            content_html: html,
            autosave,
          }),
        });
        setPost(updated);
        dirtyRef.current = false;
        setState({ kind: "clean", savedAt: new Date() });
      } catch (err) {
        setState({
          kind: "error",
          message: err instanceof ClientApiError ? err.message : "Save failed.",
        });
      }
    },
    [post.id, post.excerpt, title],
  );

  // Autosave loop: every 5s while dirty.
  useEffect(() => {
    const id = setInterval(() => {
      if (dirtyRef.current) void persist(true);
    }, AUTOSAVE_INTERVAL_MS);
    return () => clearInterval(id);
  }, [persist]);

  // ⌘S / Ctrl+S - explicit save.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        void persist(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [persist]);

  const markDirty = useCallback(() => {
    dirtyRef.current = true;
    setState((s) => (s.kind === "saving" ? s : { kind: "dirty" }));
  }, []);

  async function runTransition(path: string, body?: object) {
    setState({ kind: "saving" });
    try {
      const updated = await callApi<PostDetail>(`/v1/posts/${post.id}/${path}`, {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
      });
      setPost(updated);
      setState({ kind: "clean", savedAt: new Date() });
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof ClientApiError ? err.message : "Action failed.",
      });
    }
  }

  async function onDelete() {
    const ok = await confirmDialog({
      title: "Delete post",
      message: "This permanently removes the post and all its revisions. Continue?",
      confirmLabel: "Delete",
      tone: "danger",
    });
    if (!ok) return;
    try {
      await callApi<null>(`/v1/posts/${post.id}`, { method: "DELETE" });
      router.push("/admin/posts");
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof ClientApiError ? err.message : "Delete failed.",
      });
    }
  }

  return (
    <div className="-m-6 flex min-h-[calc(100dvh-49px)]">
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border px-6 py-3 text-sm">
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-border px-2 py-0.5 text-xs text-fg-muted">
              {post.status}
            </span>
            <SaveIndicator state={state} />
          </div>
          <ActionBar
            post={post}
            onAction={runTransition}
            onDelete={onDelete}
          />
        </header>

        <div className="mx-auto w-full max-w-3xl flex-1 space-y-4 p-6">
          <input
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              markDirty();
            }}
            placeholder="Title"
            className="w-full bg-transparent font-serif text-4xl outline-none placeholder:text-fg-subtle"
          />

          <RichEditor
            editorRef={editorRef}
            initialHtml={initialPost.content_html ?? ""}
            onChange={markDirty}
          />
        </div>
      </div>

      <MetadataDrawer post={post} allTags={allTags} onSaved={setPost} />
    </div>
  );
}

function SaveIndicator({ state }: { state: SaveState }) {
  if (state.kind === "saving") {
    return <span className="text-xs text-fg-muted">Saving…</span>;
  }
  if (state.kind === "dirty") {
    return <span className="text-xs text-fg-muted">Unsaved changes</span>;
  }
  if (state.kind === "error") {
    return (
      <span role="alert" className="text-xs text-red-600">
        {state.message}
      </span>
    );
  }
  if (state.savedAt) {
    return (
      <span className="text-xs text-fg-subtle">
        Saved at {state.savedAt.toLocaleTimeString()}
      </span>
    );
  }
  return null;
}

function ActionBar({
  post,
  onAction,
  onDelete,
}: {
  post: PostDetail;
  onAction: (path: string) => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const btn =
    "rounded-md border border-border px-3 py-1.5 text-xs hover:bg-bg-muted";
  return (
    <div className="flex gap-1">
      {post.status !== "published" && (
        <button onClick={() => onAction("publish")} className={btn} type="button">
          Publish
        </button>
      )}
      {post.status === "published" && (
        <button onClick={() => onAction("unpublish")} className={btn} type="button">
          Unpublish
        </button>
      )}
      {post.status !== "archived" && (
        <button onClick={() => onAction("archive")} className={btn} type="button">
          Archive
        </button>
      )}
      <button onClick={onDelete} className={btn + " text-red-600"} type="button">
        Delete
      </button>
    </div>
  );
}
