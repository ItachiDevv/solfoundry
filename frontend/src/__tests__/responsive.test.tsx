import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import { BREAKPOINTS, useMediaQuery, useIsMobile, useIsDesktop, useBreakpoint, useWindowSize } from '../utils/responsive';
import { TouchTarget } from '../components/common/TouchTarget';
import { ResponsiveTable, type Column } from '../components/common/ResponsiveTable';
import { ResponsiveChart } from '../components/common/ResponsiveChart';

function createMatchMedia(width: number) {
  return (query: string): MediaQueryList => {
    const minMatch = query.match(/min-width:\s*(\d+)px/);
    const maxMatch = query.match(/max-width:\s*(\d+)px/);
    let matches = false;
    if (minMatch && maxMatch) {
      matches = width >= parseInt(minMatch[1]) && width <= parseInt(maxMatch[1]);
    } else if (minMatch) {
      matches = width >= parseInt(minMatch[1]);
    } else if (maxMatch) {
      matches = width <= parseInt(maxMatch[1]);
    }
    return {
      matches, media: query, onchange: null,
      addListener: vi.fn(), removeListener: vi.fn(),
      addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
    };
  };
}

function setViewport(width: number) {
  window.matchMedia = createMatchMedia(width);
  Object.defineProperty(window, 'innerWidth', { value: width, writable: true });
}

describe('BREAKPOINTS', () => {
  it('defines four breakpoints', () => {
    expect(Object.keys(BREAKPOINTS)).toHaveLength(4);
    expect(BREAKPOINTS.sm).toBe(375);
    expect(BREAKPOINTS.md).toBe(768);
    expect(BREAKPOINTS.lg).toBe(1024);
    expect(BREAKPOINTS.xl).toBe(1440);
  });
});

describe('useMediaQuery', () => {
  beforeEach(() => setViewport(800));
  it('returns true when query matches', () => {
    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)'));
    expect(result.current).toBe(true);
  });
  it('returns false when query does not match', () => {
    setViewport(600);
    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)'));
    expect(result.current).toBe(false);
  });
});

describe('useIsMobile', () => {
  it('returns true at 375px', () => {
    setViewport(375);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
  });
  it('returns false at 768px', () => {
    setViewport(768);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
  });
});

describe('useIsDesktop', () => {
  it('returns false at 768px', () => {
    setViewport(768);
    const { result } = renderHook(() => useIsDesktop());
    expect(result.current).toBe(false);
  });
  it('returns true at 1024px', () => {
    setViewport(1024);
    const { result } = renderHook(() => useIsDesktop());
    expect(result.current).toBe(true);
  });
});

describe('useBreakpoint', () => {
  it('returns sm for small viewports', () => {
    setViewport(375);
    const { result } = renderHook(() => useBreakpoint());
    expect(result.current).toBe('sm');
  });
  it('returns md for tablet viewports', () => {
    setViewport(768);
    const { result } = renderHook(() => useBreakpoint());
    expect(result.current).toBe('md');
  });
  it('returns lg for desktop viewports', () => {
    setViewport(1024);
    const { result } = renderHook(() => useBreakpoint());
    expect(result.current).toBe('lg');
  });
  it('returns xl for wide viewports', () => {
    setViewport(1440);
    const { result } = renderHook(() => useBreakpoint());
    expect(result.current).toBe('xl');
  });
});

describe('useWindowSize', () => {
  it('returns current window dimensions', () => {
    Object.defineProperty(window, 'innerWidth', { value: 1024, writable: true });
    Object.defineProperty(window, 'innerHeight', { value: 768, writable: true });
    const { result } = renderHook(() => useWindowSize(0));
    expect(result.current.width).toBe(1024);
    expect(result.current.height).toBe(768);
  });
});

describe('TouchTarget', () => {
  it('renders as a button by default', () => {
    render(<TouchTarget aria-label="test">Click</TouchTarget>);
    const btn = screen.getByRole('button', { name: 'test' });
    expect(btn).toBeInTheDocument();
    expect(btn.tagName).toBe('BUTTON');
  });
  it('renders as an anchor when as="a"', () => {
    render(<TouchTarget as="a" href="/test" aria-label="test link">Link</TouchTarget>);
    const link = screen.getByRole('link', { name: 'test link' });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/test');
  });
  it('enforces minimum 44px dimensions via class', () => {
    render(<TouchTarget aria-label="touch">X</TouchTarget>);
    const btn = screen.getByRole('button', { name: 'touch' });
    expect(btn.className).toContain('min-w-[44px]');
    expect(btn.className).toContain('min-h-[44px]');
  });
  it('calls onClick handler', () => {
    const onClick = vi.fn();
    render(<TouchTarget onClick={onClick} aria-label="clickable">Click me</TouchTarget>);
    fireEvent.click(screen.getByRole('button', { name: 'clickable' }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

interface MockRow { id: string; name: string; value: number; }

const mockColumns: Column<MockRow>[] = [
  { key: 'name', header: 'Name', render: (row) => row.name, primary: true },
  { key: 'value', header: 'Value', render: (row) => `$${row.value}`, align: 'right' },
];

const mockData: MockRow[] = [
  { id: '1', name: 'Alpha', value: 100 },
  { id: '2', name: 'Beta', value: 200 },
];

describe('ResponsiveTable', () => {
  it('renders empty message when data is empty', () => {
    render(<ResponsiveTable columns={mockColumns} data={[]} keyExtractor={(r) => r.id} emptyMessage="No items" />);
    expect(screen.getByTestId('responsive-table-empty')).toHaveTextContent('No items');
  });

  describe('desktop mode (table)', () => {
    beforeEach(() => setViewport(1024));
    it('renders a table on desktop', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      expect(screen.getByTestId('responsive-table')).toBeInTheDocument();
    });
    it('renders column headers', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Value')).toBeInTheDocument();
    });
    it('renders row data', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      expect(screen.getByText('Alpha')).toBeInTheDocument();
      expect(screen.getByText('$200')).toBeInTheDocument();
    });
  });

  describe('mobile mode (cards)', () => {
    beforeEach(() => setViewport(375));
    it('renders cards on mobile', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      expect(screen.getByTestId('responsive-table-cards')).toBeInTheDocument();
    });
    it('renders individual card items', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      expect(screen.getByTestId('responsive-card-1')).toBeInTheDocument();
      expect(screen.getByTestId('responsive-card-2')).toBeInTheDocument();
    });
  });
});

describe('ResponsiveChart', () => {
  it('renders title and subtitle', () => {
    render(<ResponsiveChart title="Earnings" subtitle="Last 30 days"><div>Chart</div></ResponsiveChart>);
    expect(screen.getByText('Earnings')).toBeInTheDocument();
    expect(screen.getByText('Last 30 days')).toBeInTheDocument();
  });

  describe('desktop mode', () => {
    beforeEach(() => setViewport(1024));
    it('renders chart content directly', () => {
      render(<ResponsiveChart title="Test"><div data-testid="chart-inner">Chart</div></ResponsiveChart>);
      expect(screen.getByTestId('responsive-chart-desktop')).toBeInTheDocument();
      expect(screen.getByTestId('chart-inner')).toBeInTheDocument();
    });
  });

  describe('mobile mode', () => {
    beforeEach(() => setViewport(375));
    it('renders scrollable container when no mobileContent', () => {
      render(<ResponsiveChart title="Test"><div>Wide chart</div></ResponsiveChart>);
      expect(screen.getByTestId('responsive-chart-scroll')).toBeInTheDocument();
    });
    it('renders mobile content when provided', () => {
      render(
        <ResponsiveChart title="Test" mobileContent={<div data-testid="simple-chart">Simple</div>}>
          <div>Full chart</div>
        </ResponsiveChart>,
      );
      expect(screen.getByTestId('responsive-chart-mobile')).toBeInTheDocument();
      expect(screen.getByTestId('simple-chart')).toBeInTheDocument();
    });
    it('shows scroll hint initially', () => {
      render(<ResponsiveChart title="Test"><div>Wide chart</div></ResponsiveChart>);
      expect(screen.getByTestId('scroll-hint')).toBeInTheDocument();
    });
  });

  it('renders header right content', () => {
    setViewport(1024);
    render(
      <ResponsiveChart title="Earnings" headerRight={<span data-testid="total">$1,234</span>}>
        <div>Chart</div>
      </ResponsiveChart>,
    );
    expect(screen.getByTestId('total')).toHaveTextContent('$1,234');
  });
});
