import { Skeleton } from "@/components/ui/skeleton";

export default function CommentsLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-9 w-32" />
      <Skeleton className="h-4 w-2/3" />
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-border bg-bg-elevated p-4">
            <Skeleton className="mb-2 h-4 w-40" />
            <Skeleton className="mb-2 h-3 w-full" />
            <Skeleton className="h-3 w-5/6" />
          </div>
        ))}
      </div>
    </div>
  );
}
