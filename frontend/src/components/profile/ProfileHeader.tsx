import type { ReputationBadge } from '../../types/profile';

interface ProfileHeaderProps {
  githubUsername: string;
  githubAvatar: string;
  walletAddress: string;
  joinDate: string;
  reputationScore: number;
  reputationBadge: ReputationBadge;
}

const BADGE_CONFIG: Record<ReputationBadge, { label: string; color: string; bgColor: string }> = {
  newcomer: { label: 'Newcomer', color: 'text-gray-400', bgColor: 'bg-gray-800' },
  contributor: { label: 'Contributor', color: 'text-blue-400', bgColor: 'bg-blue-500/10' },
  expert: { label: 'Expert', color: 'text-[#9945FF]', bgColor: 'bg-[#9945FF]/10' },
  elite: { label: 'Elite', color: 'text-[#14F195]', bgColor: 'bg-[#14F195]/10' },
  legend: { label: 'Legend', color: 'text-yellow-400', bgColor: 'bg-yellow-400/10' },
};

function truncateWallet(address: string): string {
  if (address.length <= 10) return address;
  return `${address.slice(0, 4)}...${address.slice(-4)}`;
}

function formatJoinDate(isoDate: string): string {
  const date = new Date(isoDate);
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
}

export function ProfileHeader({
  githubUsername,
  githubAvatar,
  walletAddress,
  joinDate,
  reputationScore,
  reputationBadge,
}: ProfileHeaderProps) {
  const badge = BADGE_CONFIG[reputationBadge];

  return (
    <div
      className="relative overflow-hidden rounded-xl border border-gray-800 bg-[#111111] p-6"
      data-testid="profile-header"
    >
      {/* Background gradient accent */}
      <div className="absolute top-0 left-0 right-0 h-24 bg-gradient-to-r from-[#9945FF]/20 to-[#14F195]/20" />

      <div className="relative flex flex-col sm:flex-row items-start sm:items-center gap-5">
        {/* Avatar */}
        {githubAvatar ? (
          <img
            src={githubAvatar}
            alt={`${githubUsername}'s avatar`}
            className="h-20 w-20 rounded-full border-4 border-[#111111] shadow-lg"
            data-testid="profile-avatar"
          />
        ) : (
          <div
            className="h-20 w-20 rounded-full border-4 border-[#111111] shadow-lg bg-gradient-to-br from-[#9945FF] to-[#14F195] flex items-center justify-center text-2xl font-bold text-white"
            data-testid="profile-avatar"
            aria-label={`${githubUsername}'s avatar placeholder`}
          >
            {githubUsername.charAt(0).toUpperCase()}
          </div>
        )}

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold text-white truncate" data-testid="profile-username">
              {githubUsername}
            </h1>
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${badge.color} ${badge.bgColor}`}
              data-testid="profile-badge"
            >
              {badge.label}
            </span>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-gray-400">
            {/* Wallet address */}
            {walletAddress && (
            <span className="inline-flex items-center gap-1.5" data-testid="profile-wallet">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a2.25 2.25 0 0 0-2.25-2.25H15a3 3 0 1 1-6 0H5.25A2.25 2.25 0 0 0 3 12m18 0v6a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18v-6m18 0V9M3 12V9m18 0a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 9m18 0V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v3" />
              </svg>
              {truncateWallet(walletAddress)}
            </span>
            )}

            {/* Join date */}
            <span className="inline-flex items-center gap-1.5" data-testid="profile-join-date">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
              </svg>
              Joined {formatJoinDate(joinDate)}
            </span>

            {/* Reputation score */}
            <span className="inline-flex items-center gap-1.5" data-testid="profile-reputation-score">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
              </svg>
              {reputationScore.toLocaleString()} rep
            </span>
          </div>
        </div>

        {/* GitHub link */}
        <a
          href={`https://github.com/${githubUsername}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-lg border border-gray-700 bg-transparent px-4 py-2 text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#9945FF]"
          data-testid="profile-github-link"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12Z" />
          </svg>
          GitHub
        </a>
      </div>
    </div>
  );
}
