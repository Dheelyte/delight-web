"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { callApi } from "@/lib/client-api";
import type { PostDetail } from "@/lib/types";

export function NewPostButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function onClick() {
    setBusy(true);
    try {
      const post = await callApi<PostDetail>("/v1/posts", {
        method: "POST",
        body: JSON.stringify({ title: "Untitled" }),
      });
      router.push(`/admin/posts/${post.id}/edit`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-fg disabled:opacity-60"
    >
      {busy ? "Creating…" : "New post"}
    </button>
  );
}
