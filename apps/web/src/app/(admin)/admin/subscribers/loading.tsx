import { Skeleton } from "@/components/ui/skeleton";

export default function SubscribersLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-9 w-40" />
      <div className="flex gap-1">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-7 w-24" />
        ))}
      </div>
      <div className="overflow-hidden rounded-lg border border-border bg-bg-elevated">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="border-b border-border px-4 py-3 last:border-b-0">
            <Skeleton className="h-4 w-1/3" />
          </div>
        ))}
      </div>
    </div>
  );
}
