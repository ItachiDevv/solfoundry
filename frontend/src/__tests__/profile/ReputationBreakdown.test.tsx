import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ReputationBreakdown } from '../../components/profile/ReputationBreakdown';
import type { ReputationCategory } from '../../types/profile';

const sampleCategories: ReputationCategory[] = [
  { label: 'Bounty Completions', description: 'Points for completing bounties', points: 720, maxPoints: 1000 },
  { label: 'Code Quality', description: 'Based on review scores', points: 380, maxPoints: 500 },
  { label: 'Timeliness', description: 'Bonus for early delivery', points: 250, maxPoints: 300 },
];

const totalScore = 1350;

describe('ReputationBreakdown', () => {
  it('renders the reputation breakdown section', () => {
    render(<ReputationBreakdown categories={sampleCategories} totalScore={totalScore} />);
    expect(screen.getByTestId('reputation-breakdown')).toBeInTheDocument();
    expect(screen.getByText('Reputation Breakdown')).toBeInTheDocument();
  });

  it('displays total score', () => {
    render(<ReputationBreakdown categories={sampleCategories} totalScore={totalScore} />);
    expect(screen.getByTestId('reputation-total')).toHaveTextContent('1,350');
  });

  it('renders all category rows', () => {
    render(<ReputationBreakdown categories={sampleCategories} totalScore={totalScore} />);
    expect(screen.getByTestId('reputation-category-bounty-completions')).toBeInTheDocument();
    expect(screen.getByTestId('reputation-category-code-quality')).toBeInTheDocument();
    expect(screen.getByTestId('reputation-category-timeliness')).toBeInTheDocument();
  });

  it('displays category labels and descriptions', () => {
    render(<ReputationBreakdown categories={sampleCategories} totalScore={totalScore} />);
    expect(screen.getByText('Bounty Completions')).toBeInTheDocument();
    expect(screen.getByText('Points for completing bounties')).toBeInTheDocument();
    expect(screen.getByText('Code Quality')).toBeInTheDocument();
    expect(screen.getByText('Based on review scores')).toBeInTheDocument();
  });

  it('displays points and max points for each category', () => {
    render(<ReputationBreakdown categories={sampleCategories} totalScore={totalScore} />);
    expect(screen.getByText('720 / 1000')).toBeInTheDocument();
    expect(screen.getByText('380 / 500')).toBeInTheDocument();
    expect(screen.getByText('250 / 300')).toBeInTheDocument();
  });

  it('renders progress bars with correct aria attributes', () => {
    render(<ReputationBreakdown categories={sampleCategories} totalScore={totalScore} />);
    const progressBars = screen.getAllByRole('progressbar');
    expect(progressBars).toHaveLength(4);
    expect(progressBars[0]).toHaveAttribute('aria-valuenow', '720');
    expect(progressBars[0]).toHaveAttribute('aria-valuemax', '1000');
  });

  it('shows the max possible score', () => {
    render(<ReputationBreakdown categories={sampleCategories} totalScore={totalScore} />);
    expect(screen.getByText('of 1,800 max')).toBeInTheDocument();
  });

  it('calculates overall percentage correctly', () => {
    render(<ReputationBreakdown categories={sampleCategories} totalScore={totalScore} />);
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('Overall Progress')).toBeInTheDocument();
  });
});
