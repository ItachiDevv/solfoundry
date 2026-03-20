import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BountyHistory } from '../../components/profile/BountyHistory';
import type { BountyHistoryItem } from '../../types/profile';

const sampleBounties: BountyHistoryItem[] = [
  {
    id: 'bh-001',
    title: 'Implement token staking UI',
    tier: 'advanced',
    reward: 2_500,
    currency: 'USDC',
    status: 'in-progress',
    completedAt: '',
  },
  {
    id: 'bh-002',
    title: 'Build swap aggregator UI',
    tier: 'expert',
    reward: 3_000,
    currency: 'USDC',
    status: 'completed',
    completedAt: '2026-03-10T14:00:00Z',
  },
  {
    id: 'bh-003',
    title: 'Update CI pipeline',
    tier: 'starter',
    reward: 600,
    currency: 'USDC',
    status: 'expired',
    completedAt: '',
  },
];

describe('BountyHistory', () => {
  it('renders the bounty history section', () => {
    render(<BountyHistory bounties={sampleBounties} />);
    expect(screen.getByTestId('bounty-history')).toBeInTheDocument();
    expect(screen.getByText('Bounty History')).toBeInTheDocument();
  });

  it('renders the table with correct number of rows', () => {
    render(<BountyHistory bounties={sampleBounties} />);
    const table = screen.getByTestId('bounty-history-table');
    expect(table).toBeInTheDocument();
    expect(screen.getByTestId('bounty-row-bh-001')).toBeInTheDocument();
    expect(screen.getByTestId('bounty-row-bh-002')).toBeInTheDocument();
    expect(screen.getByTestId('bounty-row-bh-003')).toBeInTheDocument();
  });

  it('displays bounty titles', () => {
    render(<BountyHistory bounties={sampleBounties} />);
    expect(screen.getByText('Implement token staking UI')).toBeInTheDocument();
    expect(screen.getByText('Build swap aggregator UI')).toBeInTheDocument();
    expect(screen.getByText('Update CI pipeline')).toBeInTheDocument();
  });

  it('displays tier badges', () => {
    render(<BountyHistory bounties={sampleBounties} />);
    expect(screen.getByText('Advanced')).toBeInTheDocument();
    expect(screen.getByText('Expert')).toBeInTheDocument();
    expect(screen.getByText('Starter')).toBeInTheDocument();
  });

  it('displays rewards with currency', () => {
    render(<BountyHistory bounties={sampleBounties} />);
    expect(screen.getByText('2,500 USDC')).toBeInTheDocument();
    expect(screen.getByText('3,000 USDC')).toBeInTheDocument();
    expect(screen.getByText('600 USDC')).toBeInTheDocument();
  });

  it('displays status indicators', () => {
    render(<BountyHistory bounties={sampleBounties} />);
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Expired')).toBeInTheDocument();
  });

  it('shows dash for bounties without completion date', () => {
    render(<BountyHistory bounties={sampleBounties} />);
    const dashes = screen.getAllByText('-');
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it('renders empty state when no bounties', () => {
    render(<BountyHistory bounties={[]} />);
    expect(screen.getByText('No bounty history yet.')).toBeInTheDocument();
  });

  it('renders table headers', () => {
    render(<BountyHistory bounties={sampleBounties} />);
    expect(screen.getByText('Bounty')).toBeInTheDocument();
    expect(screen.getByText('Tier')).toBeInTheDocument();
    expect(screen.getByText('Reward')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Date')).toBeInTheDocument();
  });
});
