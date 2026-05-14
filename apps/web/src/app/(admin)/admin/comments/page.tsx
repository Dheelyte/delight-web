import { CommentsQueue } from "@/components/admin/comments-queue";
import { Pagination, parsePage } from "@/components/pagination";
import { apiFetch } from "@/lib/api";
import type { CommentList } from "@/lib/types";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 25;

export default async function AdminCommentsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const page = parsePage((await searchParams).page);
  const offset = (page - 1) * PAGE_SIZE;
  const { data } = await apiFetch<CommentList>(
    `/v1/comments?limit=${PAGE_SIZE}&offset=${offset}`,
  );
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      <h1 className="font-serif text-3xl">Comments</h1>
      <p className="text-sm text-fg-muted">
        Pending and spam-flagged comments. Approved comments are public on the
        post page.
        {totalPages > 1 ? ` Page ${page} of ${totalPages}.` : ""}
      </p>
      {/* `key` forces CommentsQueue to remount on page change so its local
          "removed after moderation" state resets to the new slice. */}
      <CommentsQueue key={page} initial={data} />
      <Pagination
        page={page}
        totalPages={totalPages}
        basePath="/admin/comments"
      />
    </div>
  );
}
