import { Skeleton } from "@/components/ui/skeleton";

export default function TagsLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-9 w-32" />
      <Skeleton className="h-9 w-full" />
      <div className="overflow-hidden rounded-lg border border-border bg-bg-elevated">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="border-b border-border px-4 py-3 last:border-b-0">
            <Skeleton className="h-4 w-1/3" />
          </div>
        ))}
      </div>
    </div>
  );
}
