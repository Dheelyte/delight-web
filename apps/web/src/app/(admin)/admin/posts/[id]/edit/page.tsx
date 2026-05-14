import { notFound } from "next/navigation";

import { PostEditor } from "@/components/admin/editor/post-editor";
import { ApiError, apiFetch } from "@/lib/api";
import type { PostDetail, Tag } from "@/lib/types";

export default async function EditPostPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  try {
    const { data: post } = await apiFetch<PostDetail>(`/v1/posts/${id}`);
    const { data: tags } = await apiFetch<Tag[]>("/v1/tags");
    return <PostEditor initialPost={post} allTags={tags} />;
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }
}
