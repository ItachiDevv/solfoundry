import { useState, useEffect, useCallback } from 'react';

/** Tailwind-aligned breakpoints (px) shared between CSS and JS. */
export const BREAKPOINTS = {
  sm: 375,
  md: 768,
  lg: 1024,
  xl: 1440,
} as const;

/** Named breakpoint key derived from BREAKPOINTS. */
export type Breakpoint = keyof typeof BREAKPOINTS;

/**
 * Subscribe to a CSS media-query and return whether it currently matches.
 * SSR-safe: returns false when window is unavailable.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    const mql = window.matchMedia(query);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    setMatches(mql.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [query]);

  return matches;
}

/**
 * Return the current named breakpoint (sm | md | lg | xl).
 * Evaluated from largest to smallest so the first matching min-width query wins.
 */
export function useBreakpoint(): Breakpoint {
  const isXl = useMediaQuery(`(min-width: ${BREAKPOINTS.xl}px)`);
  const isLg = useMediaQuery(`(min-width: ${BREAKPOINTS.lg}px)`);
  const isMd = useMediaQuery(`(min-width: ${BREAKPOINTS.md}px)`);
  if (isXl) return 'xl';
  if (isLg) return 'lg';
  if (isMd) return 'md';
  return 'sm';
}

/** True when viewport is narrower than the md breakpoint (768 px). */
export function useIsMobile(): boolean {
  return useMediaQuery(`(max-width: ${BREAKPOINTS.md - 1}px)`);
}

/** True when viewport is between md (768 px) and lg (1024 px). */
export function useIsTablet(): boolean {
  return useMediaQuery(
    `(min-width: ${BREAKPOINTS.md}px) and (max-width: ${BREAKPOINTS.lg - 1}px)`,
  );
}

/** True when viewport is at or above the lg breakpoint (1024 px). */
export function useIsDesktop(): boolean {
  return useMediaQuery(`(min-width: ${BREAKPOINTS.lg}px)`);
}

/** Live window dimensions. */
interface WindowSize { width: number; height: number; }

/**
 * Return current window dimensions, debounced to avoid layout thrash.
 * @param debounceMs - debounce interval in ms (default 150).
 */
export function useWindowSize(debounceMs = 150): WindowSize {
  const [size, setSize] = useState<WindowSize>({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0,
  });

  const handleResize = useCallback(() => {
    setSize({ width: window.innerWidth, height: window.innerHeight });
  }, []);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    const debouncedResize = () => {
      clearTimeout(timeout);
      timeout = setTimeout(handleResize, debounceMs);
    };
    window.addEventListener('resize', debouncedResize);
    return () => {
      window.removeEventListener('resize', debouncedResize);
      clearTimeout(timeout);
    };
  }, [handleResize, debounceMs]);

  return size;
}

/** Build a min-width media-query string for the given breakpoint. */
export function minWidth(bp: Breakpoint): string {
  return `(min-width: ${BREAKPOINTS[bp]}px)`;
}

/** Build a max-width media-query string for the given breakpoint. */
export function maxWidth(bp: Breakpoint): string {
  return `(max-width: ${BREAKPOINTS[bp] - 1}px)`;
}
