import { cn } from "@/lib/cn";

/**
 * Tiny shimmer placeholder for content that's still loading. Use as a leaf:
 *   <Skeleton className="h-4 w-40" />
 * or stack a few to mimic layout while data resolves.
 */
export function Skeleton({ className, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn("animate-pulse rounded-md bg-bg-muted", className)}
      {...rest}
    />
  );
}

/** Convenience: a list of N row-shaped skeletons. */
export function SkeletonList({ rows = 5, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-3", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-5 w-full" />
      ))}
    </div>
  );
}
