import type { ContributorProfileData } from '../types/profile';

export const mockContributorProfile: ContributorProfileData = {
  id: 'c-001',
  githubUsername: 'contributor42',
  githubAvatar: 'https://avatars.githubusercontent.com/u/12345678?v=4',
  walletAddress: '7xKXtg2CW87d97TXJSDpbD5jBkheTqA7ECTACjHm4Dp',
  joinDate: '2025-01-15T10:30:00Z',
  reputationScore: 1580,
  reputationBadge: 'expert',
  stats: { totalEarned: 24_850, bountiesCompleted: 18, successRate: 94.4, avgReviewScore: 4.7, currentStreak: 5 },
  monthlyEarnings: [
    { month: 'Aug 2025', amount: 1_200 }, { month: 'Sep 2025', amount: 2_800 },
    { month: 'Oct 2025', amount: 1_950 }, { month: 'Nov 2025', amount: 3_400 },
    { month: 'Dec 2025', amount: 2_100 }, { month: 'Jan 2026', amount: 4_500 },
    { month: 'Feb 2026', amount: 3_700 }, { month: 'Mar 2026', amount: 5_200 },
  ],
  bountyHistory: [
    { id: 'bh-001', title: 'Implement token staking UI', tier: 'advanced', reward: 2_500, currency: 'USDC', status: 'in-progress', completedAt: '' },
    { id: 'bh-002', title: 'Build swap aggregator UI', tier: 'expert', reward: 3_000, currency: 'USDC', status: 'completed', completedAt: '2026-03-10T14:00:00Z' },
    { id: 'bh-003', title: 'Add dark mode to docs site', tier: 'starter', reward: 500, currency: 'USDC', status: 'in-review', completedAt: '' },
    { id: 'bh-004', title: 'Refactor token module', tier: 'intermediate', reward: 1_200, currency: 'USDC', status: 'completed', completedAt: '2026-02-28T09:00:00Z' },
    { id: 'bh-005', title: 'Write integration tests for governance', tier: 'intermediate', reward: 1_200, currency: 'USDC', status: 'completed', completedAt: '2026-02-15T16:30:00Z' },
    { id: 'bh-006', title: 'Fix wallet connection edge cases', tier: 'starter', reward: 800, currency: 'USDC', status: 'completed', completedAt: '2026-01-20T11:00:00Z' },
    { id: 'bh-007', title: 'Update CI pipeline', tier: 'starter', reward: 600, currency: 'USDC', status: 'completed', completedAt: '2025-12-10T08:00:00Z' },
    { id: 'bh-008', title: 'Implement notification system', tier: 'advanced', reward: 2_200, currency: 'USDC', status: 'completed', completedAt: '2025-11-25T13:00:00Z' },
    { id: 'bh-009', title: 'Design system component library', tier: 'expert', reward: 3_500, currency: 'USDC', status: 'expired', completedAt: '' },
  ],
  reputationBreakdown: [
    { label: 'Bounty Completions', description: 'Points earned for successfully completing bounties', points: 720, maxPoints: 1000 },
    { label: 'Code Quality', description: 'Based on review scores and code quality metrics', points: 380, maxPoints: 500 },
    { label: 'Timeliness', description: 'Bonus for delivering before deadlines', points: 250, maxPoints: 300 },
    { label: 'Community', description: 'Helping others, reviews, and mentorship', points: 130, maxPoints: 200 },
    { label: 'Streak Bonus', description: 'Consecutive successful bounty completions', points: 100, maxPoints: 150 },
  ],
};

export const emptyContributorProfile: ContributorProfileData = {
  id: 'c-empty', githubUsername: 'newuser', githubAvatar: '', walletAddress: '',
  joinDate: new Date().toISOString(), reputationScore: 0, reputationBadge: 'newcomer',
  stats: { totalEarned: 0, bountiesCompleted: 0, successRate: 0, avgReviewScore: 0, currentStreak: 0 },
  monthlyEarnings: [], bountyHistory: [], reputationBreakdown: [],
};
