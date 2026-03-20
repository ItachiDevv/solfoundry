import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatsCards } from '../../components/profile/StatsCards';
import type { ContributorStats } from '../../types/profile';

const stats: ContributorStats = {
  totalEarned: 24_850,
  bountiesCompleted: 18,
  successRate: 94.4,
  avgReviewScore: 4.7,
  currentStreak: 5,
};

describe('StatsCards', () => {
  it('renders all five stat cards', () => {
    render(<StatsCards stats={stats} />);
    const grid = screen.getByTestId('stats-cards');
    expect(grid.children).toHaveLength(5);
  });

  it('renders Total Earned with formatted currency', () => {
    render(<StatsCards stats={stats} />);
    expect(screen.getByTestId('stat-card-total-earned')).toHaveTextContent('$24.9k');
  });

  it('renders Bounties Completed count', () => {
    render(<StatsCards stats={stats} />);
    expect(screen.getByTestId('stat-card-bounties-completed')).toHaveTextContent('18');
  });

  it('renders Success Rate percentage', () => {
    render(<StatsCards stats={stats} />);
    expect(screen.getByTestId('stat-card-success-rate')).toHaveTextContent('94.4%');
  });

  it('renders Avg Review Score', () => {
    render(<StatsCards stats={stats} />);
    expect(screen.getByTestId('stat-card-avg-review-score')).toHaveTextContent('4.7/5.0');
  });

  it('renders Current Streak', () => {
    render(<StatsCards stats={stats} />);
    expect(screen.getByTestId('stat-card-current-streak')).toHaveTextContent('5 bounties');
  });

  it('handles zero values', () => {
    const zeroStats: ContributorStats = {
      totalEarned: 0,
      bountiesCompleted: 0,
      successRate: 0,
      avgReviewScore: 0,
      currentStreak: 0,
    };
    render(<StatsCards stats={zeroStats} />);
    expect(screen.getByTestId('stat-card-total-earned')).toHaveTextContent('$0');
    expect(screen.getByTestId('stat-card-bounties-completed')).toHaveTextContent('0');
  });
});
