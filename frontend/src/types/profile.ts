// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Contributor Profile Types
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/** Reputation badge tiers based on cumulative score */
export type ReputationBadge = 'newcomer' | 'contributor' | 'expert' | 'elite' | 'legend';

/** Bounty tier levels */
export type BountyTier = 'starter' | 'intermediate' | 'advanced' | 'expert';

/** Bounty history item status */
export type ProfileBountyStatus = 'completed' | 'in-progress' | 'in-review' | 'expired' | 'cancelled';

/** Monthly earnings data point for the bar chart */
export interface MonthlyEarning {
  month: string; // e.g. "Jan 2026"
  amount: number;
}

/** Single bounty in the contributor's history */
export interface BountyHistoryItem {
  id: string;
  title: string;
  tier: BountyTier;
  reward: number;
  currency: string;
  status: ProfileBountyStatus;
  completedAt: string; // ISO date
}

/** Reputation category breakdown */
export interface ReputationCategory {
  label: string;
  description: string;
  points: number;
  maxPoints: number;
}

/** Contributor profile stats */
export interface ContributorStats {
  totalEarned: number;
  bountiesCompleted: number;
  successRate: number;
  avgReviewScore: number;
  currentStreak: number;
}

/** Full contributor profile */
export interface ContributorProfileData {
  id: string;
  githubUsername: string;
  githubAvatar: string;
  walletAddress: string;
  joinDate: string; // ISO date
  reputationScore: number;
  reputationBadge: ReputationBadge;
  stats: ContributorStats;
  monthlyEarnings: MonthlyEarning[];
  bountyHistory: BountyHistoryItem[];
  reputationBreakdown: ReputationCategory[];
}
