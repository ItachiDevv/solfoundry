import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EarningsChart } from '../../components/profile/EarningsChart';
import type { MonthlyEarning } from '../../types/profile';

const sampleData: MonthlyEarning[] = [
  { month: 'Jan 2026', amount: 4_500 },
  { month: 'Feb 2026', amount: 3_700 },
  { month: 'Mar 2026', amount: 5_200 },
];

describe('EarningsChart', () => {
  it('renders the chart container', () => {
    render(<EarningsChart data={sampleData} />);
    expect(screen.getByTestId('profile-earnings-chart')).toBeInTheDocument();
  });

  it('shows total earnings amount', () => {
    render(<EarningsChart data={sampleData} />);
    expect(screen.getByTestId('earnings-total')).toHaveTextContent('$13,400');
  });

  it('renders an SVG bar chart when data is provided', () => {
    render(<EarningsChart data={sampleData} />);
    const chart = screen.getByRole('img');
    expect(chart).toBeInTheDocument();
    expect(chart.tagName).toBe('svg');
  });

  it('shows empty state when no data provided', () => {
    render(<EarningsChart data={[]} />);
    expect(screen.getByText('No earnings data available')).toBeInTheDocument();
  });

  it('renders bar elements for each month', () => {
    render(<EarningsChart data={sampleData} />);
    expect(screen.getByTestId('earnings-bar-Jan 2026')).toBeInTheDocument();
    expect(screen.getByTestId('earnings-bar-Feb 2026')).toBeInTheDocument();
    expect(screen.getByTestId('earnings-bar-Mar 2026')).toBeInTheDocument();
  });

  it('renders the heading', () => {
    render(<EarningsChart data={sampleData} />);
    expect(screen.getByText('Earnings')).toBeInTheDocument();
    expect(screen.getByText('Monthly breakdown')).toBeInTheDocument();
  });
});
