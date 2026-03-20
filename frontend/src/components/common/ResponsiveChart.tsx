import { type ReactNode, useRef, useState, useEffect } from 'react';
import { useIsMobile } from '../../utils/responsive';

/** Props for ResponsiveChart. */
interface ResponsiveChartProps {
  children: ReactNode;
  mobileContent?: ReactNode;
  minWidth?: number;
  title?: string;
  subtitle?: string;
  headerRight?: ReactNode;
  className?: string;
}

/**
 * Responsive chart wrapper: renders directly on desktop, horizontally
 * scrollable on mobile. Provides an optional mobileContent slot for
 * simplified mobile visualisations. Scroll-hint re-appears when scrolled
 * back to the start.
 */
export function ResponsiveChart({
  children, mobileContent, minWidth = 500, title, subtitle, headerRight, className = '',
}: ResponsiveChartProps) {
  const isMobile = useIsMobile();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showScrollHint, setShowScrollHint] = useState(true);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !isMobile || mobileContent) return;
    const handleScroll = () => {
      // Re-enable the hint when the user scrolls back to the start
      setShowScrollHint(el.scrollLeft <= 10);
    };
    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => el.removeEventListener('scroll', handleScroll);
  }, [isMobile, mobileContent]);

  return (
    <div className={`rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 sm:p-5 ${className}`} data-testid="responsive-chart">
      {(title || headerRight) && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          {title && (
            <div>
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
              {subtitle && <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>}
            </div>
          )}
          {headerRight && <div className="text-left sm:text-right">{headerRight}</div>}
        </div>
      )}
      {isMobile && mobileContent ? (
        <div data-testid="responsive-chart-mobile">{mobileContent}</div>
      ) : isMobile ? (
        <div className="relative">
          {showScrollHint && (
            <div className="absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-gradient-to-l from-white dark:from-gray-900 to-transparent w-12 h-full flex items-center justify-end pr-1 pointer-events-none" aria-hidden="true" data-testid="scroll-hint">
              <svg className="h-5 w-5 text-gray-400 animate-pulse" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </div>
          )}
          <div ref={scrollRef} className="scroll-container" data-testid="responsive-chart-scroll">
            <div style={{ minWidth: `${minWidth}px` }}>{children}</div>
          </div>
        </div>
      ) : (
        <div data-testid="responsive-chart-desktop">{children}</div>
      )}
    </div>
  );
}
