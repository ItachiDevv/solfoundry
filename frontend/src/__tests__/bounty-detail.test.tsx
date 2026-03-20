import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BountyDetailPage } from '../components/bounty-detail/BountyDetailPage';
import { BountyHeader } from '../components/bounty-detail/BountyHeader';
import { RequirementsChecklist } from '../components/bounty-detail/RequirementsChecklist';
import { SubmissionsList } from '../components/bounty-detail/SubmissionsList';
import { mockBountyDetail } from '../data/mockBountyDetail';

// BountyDetailPage integration tests
describe('BountyDetailPage', () => {
  it('shows loading state initially', () => {
    render(<MemoryRouter><BountyDetailPage bountyId="bounty-101" /></MemoryRouter>);
    expect(screen.getByTestId('loading')).toBeInTheDocument();
  });

  it('renders header after data loads', async () => {
    render(<MemoryRouter><BountyDetailPage bountyId="bounty-101" /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('bounty-header')).toBeInTheDocument());
  });

  it('renders all content sections after load', async () => {
    render(<MemoryRouter><BountyDetailPage bountyId="bounty-101" /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('description')).toBeInTheDocument());
    expect(screen.getByTestId('requirements')).toBeInTheDocument();
    expect(screen.getByTestId('submissions')).toBeInTheDocument();
    expect(screen.getByTestId('skills')).toBeInTheDocument();
    expect(screen.getByText('Rust')).toBeInTheDocument();
  });

  it('renders SolFoundry footer branding', async () => {
    render(<MemoryRouter><BountyDetailPage bountyId="bounty-101" /></MemoryRouter>);
    await waitFor(() => expect(screen.getAllByText('SolFoundry').length).toBeGreaterThanOrEqual(1));
    const footer = screen.getByTestId('bounty-detail-page').querySelector('footer');
    expect(footer?.textContent).toContain('SolFoundry');
  });

  it('shows error for unknown bounty ID', async () => {
    render(<MemoryRouter><BountyDetailPage bountyId="unknown" /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('error')).toHaveTextContent('not found'));
  });

  it('does not render content sections on error', async () => {
    render(<MemoryRouter><BountyDetailPage bountyId="unknown" /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('error')).toBeInTheDocument());
    expect(screen.queryByTestId('bounty-header')).not.toBeInTheDocument();
  });
});

// BountyHeader
describe('BountyHeader', () => {
  it('renders bounty title', () => {
    render(<BountyHeader bounty={mockBountyDetail} />);
    expect(screen.getByTestId('bounty-title')).toHaveTextContent(mockBountyDetail.title);
  });

  it('renders tier badge with correct text', () => {
    render(<BountyHeader bounty={mockBountyDetail} />);
    expect(screen.getByText('T2')).toBeInTheDocument();
  });

  it('renders reward, currency, and project', () => {
    render(<BountyHeader bounty={mockBountyDetail} />);
    expect(screen.getByTestId('bounty-reward')).toHaveTextContent('3,500');
    expect(screen.getByText('USDC')).toBeInTheDocument();
    expect(screen.getByText('SolFoundry')).toBeInTheDocument();
  });

  it('applies T1 tier color', () => {
    const t1 = { ...mockBountyDetail, tier: 'T1' as const };
    render(<BountyHeader bounty={t1} />);
    expect(screen.getByText('T1').className).toContain('#14F195');
  });

  it('applies T3 tier color', () => {
    const t3 = { ...mockBountyDetail, tier: 'T3' as const };
    render(<BountyHeader bounty={t3} />);
    expect(screen.getByText('T3').className).toContain('#FF6B6B');
  });

  it('renders large reward with comma formatting', () => {
    const big = { ...mockBountyDetail, rewardAmount: 50000 };
    render(<BountyHeader bounty={big} />);
    expect(screen.getByTestId('bounty-reward')).toHaveTextContent('50,000');
  });
});

// RequirementsChecklist
describe('RequirementsChecklist', () => {
  it('renders heading', () => {
    render(<RequirementsChecklist requirements={mockBountyDetail.requirements} />);
    expect(screen.getByText('Requirements')).toBeInTheDocument();
  });

  it('renders all requirement items', () => {
    render(<RequirementsChecklist requirements={mockBountyDetail.requirements} />);
    mockBountyDetail.requirements.forEach((r) =>
      expect(screen.getByText(r.text)).toBeInTheDocument(),
    );
  });

  it('shows checkbox state and line-through for completed items', () => {
    render(<RequirementsChecklist requirements={[{ text: 'A', completed: false }, { text: 'B', completed: true }]} />);
    expect(screen.getByText('[ ]')).toBeInTheDocument();
    expect(screen.getByText('[x]')).toBeInTheDocument();
    expect(screen.getByText('B').className).toContain('line-through');
  });

  it('shows empty state when no requirements', () => {
    render(<RequirementsChecklist requirements={[]} />);
    expect(screen.getByTestId('requirements-empty')).toBeInTheDocument();
  });
});

// SubmissionsList
describe('SubmissionsList', () => {
  const subs = mockBountyDetail.submissions;

  it('renders heading with count', () => {
    render(<SubmissionsList submissions={subs} />);
    expect(screen.getByText('Submissions (2)')).toBeInTheDocument();
  });

  it('renders authors, status, and secure PR links', () => {
    render(<SubmissionsList submissions={subs} />);
    expect(screen.getByText('dev-alice')).toBeInTheDocument();
    expect(screen.getByText('in-review')).toBeInTheDocument();
    const links = screen.getAllByText('View PR');
    expect(links).toHaveLength(2);
    const a = links[0].closest('a');
    expect(a).toHaveAttribute('target', '_blank');
    expect(a).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('shows empty state when no submissions', () => {
    render(<SubmissionsList submissions={[]} />);
    expect(screen.getByTestId('submissions-empty')).toBeInTheDocument();
    expect(screen.getByText('Submissions (0)')).toBeInTheDocument();
  });

  it('renders correct PR URLs and test IDs', () => {
    render(<SubmissionsList submissions={subs} />);
    expect(screen.getAllByText('View PR')[0].closest('a')).toHaveAttribute('href', 'https://github.com/org/repo/pull/42');
    expect(screen.getByTestId('submission-s1')).toBeInTheDocument();
    expect(screen.getByTestId('submission-s2')).toBeInTheDocument();
  });
});
