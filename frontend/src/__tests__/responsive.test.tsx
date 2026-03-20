import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import {
  BREAKPOINTS,
  useMediaQuery,
  useIsMobile,
  useIsDesktop,
  useBreakpoint,
  useWindowSize,
} from '../utils/responsive';
import { TouchTarget } from '../components/common/TouchTarget';
import { ResponsiveTable, type Column } from '../components/common/ResponsiveTable';
import { ResponsiveChart } from '../components/common/ResponsiveChart';

// ---------------------------------------------------------------------------
// matchMedia mock that correctly handles min-width, max-width, and combined
// range queries like "(min-width: 768px) and (max-width: 1023px)".
// ---------------------------------------------------------------------------
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
      matches,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    };
  };
}

function setViewport(width: number) {
  window.matchMedia = createMatchMedia(width);
  Object.defineProperty(window, 'innerWidth', { value: width, writable: true });
}

// ---------------------------------------------------------------------------
// BREAKPOINTS — must match tailwind.config.js screens
// ---------------------------------------------------------------------------
describe('BREAKPOINTS', () => {
  it('defines sm/md/lg/xl matching Tailwind config screens', () => {
    expect(BREAKPOINTS).toEqual({ sm: 375, md: 768, lg: 1024, xl: 1440 });
  });
});

// ---------------------------------------------------------------------------
// useMediaQuery — foundation hook for all responsive behavior
// ---------------------------------------------------------------------------
describe('useMediaQuery', () => {
  beforeEach(() => setViewport(800));

  it('returns true when min-width query matches', () => {
    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)'));
    expect(result.current).toBe(true);
  });

  it('returns false when min-width query does not match', () => {
    setViewport(600);
    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)'));
    expect(result.current).toBe(false);
  });

  it('handles max-width queries correctly', () => {
    setViewport(767);
    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'));
    expect(result.current).toBe(true);
  });

  it('handles combined min+max range query', () => {
    setViewport(800);
    const { result } = renderHook(() =>
      useMediaQuery('(min-width: 768px) and (max-width: 1023px)'),
    );
    expect(result.current).toBe(true);
  });

  it('returns boolean type in all cases', () => {
    const { result } = renderHook(() => useMediaQuery('(min-width: 0px)'));
    expect(typeof result.current).toBe('boolean');
  });
});

// ---------------------------------------------------------------------------
// useIsMobile / useIsDesktop — boundary tests at exact breakpoints
// ---------------------------------------------------------------------------
describe('useIsMobile', () => {
  it('returns true at 375px (sm breakpoint)', () => {
    setViewport(375);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
  });

  it('returns true at 767px (just below md)', () => {
    setViewport(767);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
  });

  it('returns false at 768px (md breakpoint)', () => {
    setViewport(768);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
  });
});

describe('useIsDesktop', () => {
  it('returns false at 1023px (just below lg)', () => {
    setViewport(1023);
    const { result } = renderHook(() => useIsDesktop());
    expect(result.current).toBe(false);
  });

  it('returns true at 1024px (lg breakpoint)', () => {
    setViewport(1024);
    const { result } = renderHook(() => useIsDesktop());
    expect(result.current).toBe(true);
  });

  it('returns true at 1440px (xl breakpoint)', () => {
    setViewport(1440);
    const { result } = renderHook(() => useIsDesktop());
    expect(result.current).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// useBreakpoint — maps viewport widths to named breakpoints
// ---------------------------------------------------------------------------
describe('useBreakpoint', () => {
  it.each([
    [320, 'sm'],
    [375, 'sm'],
    [767, 'sm'],
    [768, 'md'],
    [1023, 'md'],
    [1024, 'lg'],
    [1439, 'lg'],
    [1440, 'xl'],
    [1920, 'xl'],
  ] as const)('returns "%s" for viewport width %dpx', (width, expected) => {
    setViewport(width);
    const { result } = renderHook(() => useBreakpoint());
    expect(result.current).toBe(expected);
  });
});

// ---------------------------------------------------------------------------
// useWindowSize
// ---------------------------------------------------------------------------
describe('useWindowSize', () => {
  it('returns current window dimensions', () => {
    Object.defineProperty(window, 'innerWidth', { value: 1024, writable: true });
    Object.defineProperty(window, 'innerHeight', { value: 768, writable: true });
    const { result } = renderHook(() => useWindowSize(0));
    expect(result.current).toEqual({ width: 1024, height: 768 });
  });
});

// ---------------------------------------------------------------------------
// TouchTarget — enforces WCAG 2.5.8 minimum 44px touch target
// ---------------------------------------------------------------------------
describe('TouchTarget', () => {
  it('renders as a button by default', () => {
    render(<TouchTarget aria-label="test">Click</TouchTarget>);
    const btn = screen.getByRole('button', { name: 'test' });
    expect(btn).toBeInTheDocument();
    expect(btn.tagName).toBe('BUTTON');
  });

  it('renders as an anchor when as="a"', () => {
    render(<TouchTarget as="a" href="/test" aria-label="link">Link</TouchTarget>);
    const link = screen.getByRole('link', { name: 'link' });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/test');
  });

  it('renders as a div when as="div"', () => {
    render(<TouchTarget as="div" role="menuitem" aria-label="item">Item</TouchTarget>);
    const el = screen.getByRole('menuitem', { name: 'item' });
    expect(el.tagName).toBe('DIV');
  });

  it('enforces 44px minimum via min-w-[44px] and min-h-[44px] utility classes', () => {
    render(<TouchTarget aria-label="touch">X</TouchTarget>);
    const btn = screen.getByRole('button', { name: 'touch' });
    // Single source of truth: Tailwind utility classes on the component.
    // No duplicate .touch-target CSS class or Tailwind config 'touch' spacing.
    expect(btn.className).toContain('min-w-[44px]');
    expect(btn.className).toContain('min-h-[44px]');
  });

  it('includes touch-manipulation for fast tap response', () => {
    render(<TouchTarget aria-label="fast">Tap</TouchTarget>);
    const btn = screen.getByRole('button', { name: 'fast' });
    expect(btn.className).toContain('touch-manipulation');
  });

  it('merges custom className with base classes', () => {
    render(<TouchTarget className="bg-red-500" aria-label="styled">S</TouchTarget>);
    const btn = screen.getByRole('button', { name: 'styled' });
    expect(btn.className).toContain('min-w-[44px]');
    expect(btn.className).toContain('bg-red-500');
  });

  it('calls onClick handler', () => {
    const onClick = vi.fn();
    render(<TouchTarget onClick={onClick} aria-label="clickable">Click</TouchTarget>);
    fireEvent.click(screen.getByRole('button', { name: 'clickable' }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('sets type="button" to prevent accidental form submission', () => {
    render(<TouchTarget aria-label="safe">Safe</TouchTarget>);
    expect(screen.getByRole('button', { name: 'safe' })).toHaveAttribute('type', 'button');
  });
});

// ---------------------------------------------------------------------------
// ResponsiveTable — integration test: table-to-card switching
// ---------------------------------------------------------------------------
interface MockRow {
  id: string;
  name: string;
  value: number;
  status: string;
}

const mockColumns: Column<MockRow>[] = [
  { key: 'name', header: 'Name', render: (row) => row.name, primary: true },
  { key: 'value', header: 'Value', render: (row) => `$${row.value}`, align: 'right' },
  { key: 'status', header: 'Status', render: (row) => row.status, hideOnMobile: true },
];

const mockData: MockRow[] = [
  { id: '1', name: 'Alpha', value: 100, status: 'Active' },
  { id: '2', name: 'Beta', value: 200, status: 'Pending' },
  { id: '3', name: 'Gamma', value: 300, status: 'Closed' },
];

describe('ResponsiveTable', () => {
  it('renders empty message when data is empty', () => {
    render(
      <ResponsiveTable
        columns={mockColumns}
        data={[]}
        keyExtractor={(r) => r.id}
        emptyMessage="Nothing here"
      />,
    );
    expect(screen.getByTestId('responsive-table-empty')).toHaveTextContent('Nothing here');
  });

  describe('desktop (>= 768px) — renders HTML <table>', () => {
    beforeEach(() => setViewport(1024));

    it('renders a <table> element with data-testid', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      const table = screen.getByTestId('responsive-table');
      expect(table.tagName).toBe('TABLE');
    });

    it('renders all column headers including hideOnMobile columns', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Value')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    it('renders all row data correctly', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      expect(screen.getByText('Alpha')).toBeInTheDocument();
      expect(screen.getByText('$200')).toBeInTheDocument();
      expect(screen.getByText('Closed')).toBeInTheDocument();
    });

    it('does NOT render card layout on desktop', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      expect(screen.queryByTestId('responsive-table-cards')).not.toBeInTheDocument();
    });

    it('renders table rows with correct test IDs', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      expect(screen.getByTestId('responsive-row-1')).toBeInTheDocument();
      expect(screen.getByTestId('responsive-row-2')).toBeInTheDocument();
      expect(screen.getByTestId('responsive-row-3')).toBeInTheDocument();
    });
  });

  describe('mobile (< 768px) — renders stacked cards', () => {
    beforeEach(() => setViewport(375));

    it('renders card container with role="list"', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      const cards = screen.getByTestId('responsive-table-cards');
      expect(cards).toHaveAttribute('role', 'list');
    });

    it('renders one card per data row with listitem role', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      const card1 = screen.getByTestId('responsive-card-1');
      const card2 = screen.getByTestId('responsive-card-2');
      const card3 = screen.getByTestId('responsive-card-3');
      expect(card1).toHaveAttribute('role', 'listitem');
      expect(card2).toHaveAttribute('role', 'listitem');
      expect(card3).toHaveAttribute('role', 'listitem');
    });

    it('does NOT render <table> on mobile', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      expect(screen.queryByTestId('responsive-table')).not.toBeInTheDocument();
    });

    it('renders primary columns prominently in card', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      const card = screen.getByTestId('responsive-card-1');
      expect(within(card).getByText('Alpha')).toBeInTheDocument();
    });

    it('hides columns marked hideOnMobile in cards', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      const card = screen.getByTestId('responsive-card-1');
      // Status is hideOnMobile, so "Active" should not appear
      expect(within(card).queryByText('Active')).not.toBeInTheDocument();
    });

    it('renders detail columns as label-value pairs', () => {
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      const card = screen.getByTestId('responsive-card-1');
      expect(within(card).getByText('Value')).toBeInTheDocument();
      expect(within(card).getByText('$100')).toBeInTheDocument();
    });

    it('renders cardAction when provided', () => {
      render(
        <ResponsiveTable
          columns={mockColumns}
          data={mockData}
          keyExtractor={(r) => r.id}
          cardAction={(row) => <button data-testid={`action-${row.id}`}>View</button>}
        />,
      );
      expect(screen.getByTestId('action-1')).toBeInTheDocument();
      expect(screen.getByTestId('action-2')).toBeInTheDocument();
    });
  });

  describe('breakpoint boundary — switches at md (768px)', () => {
    it('renders cards at 767px (just below md)', () => {
      setViewport(767);
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      expect(screen.getByTestId('responsive-table-cards')).toBeInTheDocument();
      expect(screen.queryByTestId('responsive-table')).not.toBeInTheDocument();
    });

    it('renders table at 768px (exactly md)', () => {
      setViewport(768);
      render(<ResponsiveTable columns={mockColumns} data={mockData} keyExtractor={(r) => r.id} />);
      expect(screen.getByTestId('responsive-table')).toBeInTheDocument();
      expect(screen.queryByTestId('responsive-table-cards')).not.toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// ResponsiveChart — integration test: desktop vs mobile rendering
// ---------------------------------------------------------------------------
describe('ResponsiveChart', () => {
  it('renders title and subtitle', () => {
    setViewport(1024);
    render(
      <ResponsiveChart title="Earnings" subtitle="Last 30 days">
        <div>Chart</div>
      </ResponsiveChart>,
    );
    expect(screen.getByText('Earnings')).toBeInTheDocument();
    expect(screen.getByText('Last 30 days')).toBeInTheDocument();
  });

  describe('desktop mode', () => {
    beforeEach(() => setViewport(1024));

    it('renders chart content without scroll container', () => {
      render(
        <ResponsiveChart title="Test">
          <div data-testid="chart-inner">Chart</div>
        </ResponsiveChart>,
      );
      expect(screen.getByTestId('responsive-chart-desktop')).toBeInTheDocument();
      expect(screen.getByTestId('chart-inner')).toBeInTheDocument();
      expect(screen.queryByTestId('responsive-chart-scroll')).not.toBeInTheDocument();
    });
  });

  describe('mobile mode', () => {
    beforeEach(() => setViewport(375));

    it('wraps chart in scrollable container when no mobileContent', () => {
      render(
        <ResponsiveChart title="Test">
          <div>Wide chart</div>
        </ResponsiveChart>,
      );
      expect(screen.getByTestId('responsive-chart-scroll')).toBeInTheDocument();
      expect(screen.queryByTestId('responsive-chart-desktop')).not.toBeInTheDocument();
    });

    it('scroll container uses .scroll-container class from responsive.css', () => {
      render(
        <ResponsiveChart title="Test">
          <div>Wide chart</div>
        </ResponsiveChart>,
      );
      const scrollEl = screen.getByTestId('responsive-chart-scroll');
      expect(scrollEl.className).toContain('scroll-container');
    });

    it('renders alternative mobileContent when provided', () => {
      render(
        <ResponsiveChart
          title="Test"
          mobileContent={<div data-testid="simple-chart">Simple</div>}
        >
          <div>Full chart</div>
        </ResponsiveChart>,
      );
      expect(screen.getByTestId('responsive-chart-mobile')).toBeInTheDocument();
      expect(screen.getByTestId('simple-chart')).toBeInTheDocument();
      expect(screen.queryByTestId('responsive-chart-scroll')).not.toBeInTheDocument();
    });

    it('shows accessible scroll hint', () => {
      render(
        <ResponsiveChart title="Test">
          <div>Wide chart</div>
        </ResponsiveChart>,
      );
      const hint = screen.getByTestId('scroll-hint');
      expect(hint).toBeInTheDocument();
      expect(hint).toHaveAttribute('aria-hidden', 'true');
    });
  });

  it('renders headerRight content', () => {
    setViewport(1024);
    render(
      <ResponsiveChart title="Earnings" headerRight={<span data-testid="total">$1,234</span>}>
        <div>Chart</div>
      </ResponsiveChart>,
    );
    expect(screen.getByTestId('total')).toHaveTextContent('$1,234');
  });
});
