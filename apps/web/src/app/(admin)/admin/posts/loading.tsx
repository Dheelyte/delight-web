import { Skeleton } from "@/components/ui/skeleton";

export default function PostsLoading() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-9 w-32" />
        <Skeleton className="h-8 w-24" />
      </div>
      <div className="flex flex-wrap gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-7 w-20" />
        ))}
      </div>
      <div className="overflow-hidden rounded-lg border border-border bg-bg-elevated">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="border-b border-border px-4 py-3 last:border-b-0">
            <Skeleton className="mb-2 h-4 w-2/3" />
            <Skeleton className="h-3 w-1/4" />
          </div>
        ))}
      </div>
    </div>
  );
}
