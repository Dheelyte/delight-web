import { Skeleton } from "@/components/ui/skeleton";

export default function SeriesLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-9 w-32" />
      <div className="overflow-hidden rounded-lg border border-border bg-bg-elevated">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="border-b border-border px-4 py-3 last:border-b-0">
            <Skeleton className="mb-2 h-4 w-1/2" />
            <Skeleton className="h-3 w-1/4" />
          </div>
        ))}
      </div>
    </div>
  );
}
