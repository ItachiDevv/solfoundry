/**
 * Reusable loading skeleton components for data-fetching states.
 * Pulse-animated placeholders matching card/table/grid layouts.
 * @module components/LoadingSkeleton
 */
import React from 'react';

/** Single animated bar. */
function Bar({ w = 'w-full', h = 'h-4' }: { w?: string; h?: string }) {
  return <div className={`${w} ${h} bg-gray-700 rounded animate-pulse`} />;
}

/** Card skeleton matching stat card layout. */
export function CardSkeleton(): React.ReactElement {
  return (
    <div className="rounded-xl border border-gray-700 bg-surface-100 p-4 space-y-3">
      <Bar w="w-24" h="h-3" /><Bar w="w-16" h="h-6" /><Bar w="w-32" h="h-3" />
    </div>
  );
}

/** Grid of card skeletons. */
export function GridSkeleton({ count = 4 }: { count?: number }): React.ReactElement {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Array.from({ length: count }, (_, i) => <CardSkeleton key={i} />)}
    </div>
  );
}

/** Table row skeletons. */
export function TableSkeleton({ rows = 5 }: { rows?: number }): React.ReactElement {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-4 p-3 rounded-lg bg-surface-100">
          <Bar w="w-8" h="h-8" />
          <div className="flex-1 space-y-2"><Bar w="w-40" h="h-4" /><Bar w="w-24" h="h-3" /></div>
          <Bar w="w-16" h="h-4" />
        </div>
      ))}
    </div>
  );
}

/** Full-page loading skeleton with accessible label. */
export function PageSkeleton({ label = 'Loading data' }: { label?: string }): React.ReactElement {
  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6" role="status" aria-label={label}>
      <Bar w="w-48" h="h-8" /><GridSkeleton count={4} /><TableSkeleton rows={3} />
      <span className="sr-only">{label}...</span>
    </div>
  );
}
