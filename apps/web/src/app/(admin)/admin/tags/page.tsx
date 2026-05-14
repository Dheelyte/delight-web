import { TagManager } from "@/components/admin/tag-manager";
import { apiFetch } from "@/lib/api";
import type { Tag } from "@/lib/types";

export default async function TagsPage() {
  const { data: tags } = await apiFetch<Tag[]>("/v1/tags");
  return (
    <div className="space-y-4">
      <h1 className="font-serif text-3xl">Tags</h1>
      <TagManager initialTags={tags} />
    </div>
  );
}
