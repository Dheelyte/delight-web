import { Skeleton, SkeletonList } from "@/components/ui/skeleton";

export default function AdminLoading() {
  return (
    <div className="space-y-8">
      <Skeleton className="h-9 w-48" />
      <div className="grid gap-4 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-bg-elevated p-4">
          <Skeleton className="mb-4 h-4 w-32" />
          <SkeletonList rows={4} />
        </div>
        <div className="rounded-lg border border-border bg-bg-elevated p-4">
          <Skeleton className="mb-4 h-4 w-32" />
          <SkeletonList rows={4} />
        </div>
      </div>
    </div>
  );
}
