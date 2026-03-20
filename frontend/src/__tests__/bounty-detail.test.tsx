import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BountyDetailPage } from '../components/bounty-detail/BountyDetailPage';
import { BountyHeader } from '../components/bounty-detail/BountyHeader';
import { RequirementsChecklist } from '../components/bounty-detail/RequirementsChecklist';
import { SubmissionsList } from '../components/bounty-detail/SubmissionsList';
import { mockBountyDetail } from '../data/mockBountyDetail';

describe('BountyDetailPage with Sidebar', () => {
  it('renders sidebar and detail content after loading', async () => {
    render(<MemoryRouter><BountyDetailPage bountyId="bounty-101" /></MemoryRouter>);
    expect(screen.getByLabelText('Main navigation')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('bounty-detail')).toBeInTheDocument());
    await waitFor(() => expect(screen.getByTestId('bounty-header')).toBeInTheDocument());
  });
  it('shows error for unknown bounty', async () => {
    render(<MemoryRouter><BountyDetailPage bountyId="unknown" /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('error')).toHaveTextContent('not found'));
  });
});
describe('BountyHeader', () => {
  it('renders title, tier, reward, and project', () => {
    render(<BountyHeader bounty={mockBountyDetail} />);
    expect(screen.getByText(mockBountyDetail.title)).toBeInTheDocument();
    expect(screen.getByText('T2')).toBeInTheDocument();
    expect(screen.getByText('3500')).toBeInTheDocument();
    expect(screen.getByText('USDC')).toBeInTheDocument();
    expect(screen.getByText('SolFoundry')).toBeInTheDocument();
  });
});
describe('RequirementsChecklist', () => {
  it('renders all requirements', () => {
    render(<RequirementsChecklist requirements={mockBountyDetail.requirements} />);
    expect(screen.getByText('Requirements')).toBeInTheDocument();
    mockBountyDetail.requirements.forEach(r => expect(screen.getByText(r.text)).toBeInTheDocument());
  });
});
describe('SubmissionsList', () => {
  it('renders submissions with status and PR links', () => {
    render(<SubmissionsList submissions={mockBountyDetail.submissions} />);
    expect(screen.getByText('dev-alice')).toBeInTheDocument();
    expect(screen.getByText('in-review')).toBeInTheDocument();
    expect(screen.getAllByText('View PR').length).toBe(2);
  });
  it('shows empty message when no submissions', () => {
    render(<SubmissionsList submissions={[]} />);
    expect(screen.getByText('No submissions yet.')).toBeInTheDocument();
  });
});
