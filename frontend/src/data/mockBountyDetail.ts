import type { BountyDetail } from '../types/bountyDetail';
const d = (days: number) => new Date(Date.now() + days * 864e5).toISOString();
/** Mock bounty for development and testing. */
export const mockBountyDetail: BountyDetail = {
  id: 'bounty-101', title: 'Fix token transfer edge case in escrow program',
  description: 'The escrow program panics when a token account has been closed during cancellation.\n\n## Steps to reproduce\n1. Create escrow with SPL token\n2. Close the token account externally\n3. Cancel escrow -> panic',
  tier: 'T2', skills: ['Rust', 'Anchor', 'Solana'], rewardAmount: 3500, currency: 'USDC', deadline: d(7), status: 'open',
  requirements: [{ text: 'Add closed-account check before transfer', completed: false }, { text: 'Add unit tests for edge case', completed: false }, { text: 'Update IDL documentation', completed: false }],
  submissions: [
    { id: 's1', author: 'dev-alice', prUrl: 'https://github.com/org/repo/pull/42', status: 'in-review', createdAt: d(-2) },
    { id: 's2', author: 'dev-bob', prUrl: 'https://github.com/org/repo/pull/45', status: 'pending', createdAt: d(-1) },
  ],
  createdAt: d(-5), projectName: 'SolFoundry', creatorName: 'SolFoundry Core',
};
/** Completed bounty variant for testing. */
export const mockCompletedBounty: BountyDetail = {
  ...mockBountyDetail, id: 'bounty-102', title: 'Build staking dashboard', tier: 'T3', status: 'completed', rewardAmount: 15000, deadline: d(-3),
  submissions: [{ id: 's3', author: 'dev-carol', prUrl: 'https://github.com/org/repo/pull/50', status: 'approved', createdAt: d(-5) }],
};
export const mockBounties: BountyDetail[] = [mockBountyDetail, mockCompletedBounty];
