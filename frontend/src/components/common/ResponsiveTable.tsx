import { type ReactNode } from 'react';
import { useIsMobile } from '../../utils/responsive';

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  primary?: boolean;
  hideOnMobile?: boolean;
  align?: 'left' | 'center' | 'right';
  minWidth?: string;
}

interface ResponsiveTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (row: T) => string;
  emptyMessage?: string;
  cardAction?: (row: T) => ReactNode;
  className?: string;
}

export function ResponsiveTable<T>({
  columns, data, keyExtractor, emptyMessage = 'No data available', cardAction, className = '',
}: ResponsiveTableProps<T>) {
  const isMobile = useIsMobile();

  if (data.length === 0) {
    return (
      <div className={`text-center py-8 text-gray-400 dark:text-gray-500 text-sm ${className}`} data-testid="responsive-table-empty">
        {emptyMessage}
      </div>
    );
  }

  if (isMobile) {
    return (
      <div className={`space-y-3 ${className}`} data-testid="responsive-table-cards" role="list">
        {data.map((row) => {
          const key = keyExtractor(row);
          const primaryCols = columns.filter((c) => c.primary);
          const detailCols = columns.filter((c) => !c.primary && !c.hideOnMobile);
          return (
            <div key={key} className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 space-y-3" role="listitem" data-testid={`responsive-card-${key}`}>
              {primaryCols.length > 0 && (
                <div className="space-y-1">
                  {primaryCols.map((col) => (
                    <div key={col.key} className="text-sm font-semibold text-gray-900 dark:text-white">{col.render(row)}</div>
                  ))}
                </div>
              )}
              <div className="space-y-2">
                {detailCols.map((col) => (
                  <div key={col.key} className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400 shrink-0">{col.header}</span>
                    <span className="text-sm text-gray-900 dark:text-white text-right min-w-0">{col.render(row)}</span>
                  </div>
                ))}
              </div>
              {cardAction && <div className="pt-2 border-t border-gray-100 dark:border-gray-800">{cardAction(row)}</div>}
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className={`scroll-container rounded-xl border border-gray-200 dark:border-gray-800 ${className}`}>
      <table className="w-full text-sm" data-testid="responsive-table">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
            {columns.map((col) => (
              <th key={col.key} className={`px-4 py-3 font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap ${col.align === 'center' ? 'text-center' : col.align === 'right' ? 'text-right' : 'text-left'}`} style={col.minWidth ? { minWidth: col.minWidth } : undefined}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
          {data.map((row) => (
            <tr key={keyExtractor(row)} className="bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors" data-testid={`responsive-row-${keyExtractor(row)}`}>
              {columns.map((col) => (
                <td key={col.key} className={`px-4 py-3 text-gray-900 dark:text-white whitespace-nowrap ${col.align === 'center' ? 'text-center' : col.align === 'right' ? 'text-right' : 'text-left'}`}>
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
