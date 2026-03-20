import type { ContributorProfileData } from '../../types/profile';
import { ProfileHeader } from './ProfileHeader';
import { StatsCards } from './StatsCards';
import { EarningsChart } from './EarningsChart';
import { BountyHistory } from './BountyHistory';
import { ReputationBreakdown } from './ReputationBreakdown';

interface ContributorProfileProps {
  profile: ContributorProfileData;
}

export function ContributorProfile({ profile }: ContributorProfileProps) {
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white font-mono" data-testid="contributor-profile">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Profile Header */}
        <ProfileHeader
          githubUsername={profile.githubUsername}
          githubAvatar={profile.githubAvatar}
          walletAddress={profile.walletAddress}
          joinDate={profile.joinDate}
          reputationScore={profile.reputationScore}
          reputationBadge={profile.reputationBadge}
        />

        {/* Stats Cards */}
        <StatsCards stats={profile.stats} />

        {/* Charts & Reputation - two column layout on large screens */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <EarningsChart data={profile.monthlyEarnings} />
          <ReputationBreakdown
            categories={profile.reputationBreakdown}
            totalScore={profile.reputationScore}
          />
        </div>

        {/* Bounty History */}
        <BountyHistory bounties={profile.bountyHistory} />

        {/* Hire as Agent button (placeholder) */}
        <div className="flex justify-center pt-4">
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#9945FF] to-[#14F195] px-8 py-3 text-base font-semibold text-white shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#9945FF] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a0a] disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="hire-agent-button"
            onClick={() => {
              // Placeholder - will integrate with agent hiring flow
            }}
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
            </svg>
            Hire as Agent
          </button>
        </div>
      </div>
    </div>
  );
}
