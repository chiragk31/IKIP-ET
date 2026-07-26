/**
 * WidgetSkeleton — Shared loading skeleton for all dashboard widgets
 */

export function WidgetSkeleton({ rows = 4, height = 12 }: { rows?: number; height?: number }) {
  return (
    <div className="space-y-2 p-4" aria-label="Loading...">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="skeleton rounded"
          style={{ height: `${height}px`, opacity: 1 - i * 0.15 }}
        />
      ))}
    </div>
  );
}

/**
 * KpiSkeleton — Skeleton for overview KPI cards
 */
export function KpiSkeleton() {
  return (
    <div className="widget p-4 space-y-3">
      <div className="skeleton h-3 w-16 rounded" />
      <div className="skeleton h-8 w-24 rounded" />
      <div className="skeleton h-2 w-full rounded" />
    </div>
  );
}
