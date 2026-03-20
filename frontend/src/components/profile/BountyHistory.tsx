import type { BountyHistoryItem, BountyTier, ProfileBountyStatus } from '../../types/profile';

interface BountyHistoryProps {
  bounties: BountyHistoryItem[];
}

const STATUS_CONFIG: Record<ProfileBountyStatus, { label: string; dotClass: string; textClass: string }> = {
  'completed': { label: 'Completed', dotClass: 'bg-[#14F195]', textClass: 'text-[#14F195]' },
  'in-progress': { label: 'In Progress', dotClass: 'bg-yellow-400', textClass: 'text-yellow-400' },
  'in-review': { label: 'In Review', dotClass: 'bg-blue-400', textClass: 'text-blue-400' },
  'expired': { label: 'Expired', dotClass: 'bg-red-500', textClass: 'text-red-500' },
  'cancelled': { label: 'Cancelled', dotClass: 'bg-gray-500', textClass: 'text-gray-500' },
};

const TIER_CONFIG: Record<BountyTier, { label: string; color: string; bg: string }> = {
  starter: { label: 'Starter', color: 'text-gray-400', bg: 'bg-gray-800' },
  intermediate: { label: 'Intermediate', color: 'text-blue-400', bg: 'bg-blue-500/10' },
  advanced: { label: 'Advanced', color: 'text-[#9945FF]', bg: 'bg-[#9945FF]/10' },
  expert: { label: 'Expert', color: 'text-[#14F195]', bg: 'bg-[#14F195]/10' },
};

function formatDate(isoDate: string): string {
  if (!isoDate) return '-';
  const date = new Date(isoDate);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function BountyHistory({ bounties }: BountyHistoryProps) {
  return (
    <div className="rounded-xl border border-gray-800 bg-[#111111] p-5" data-testid="bounty-history">
      <h3 className="text-lg font-semibold text-white mb-4">Bounty History</h3>

      {bounties.length === 0 ? (
        <p className="text-gray-500 text-sm py-8 text-center" data-testid="bounty-history-empty">No bounty history yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="bounty-history-table">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left py-3 px-2 text-gray-500 font-medium">Bounty</th>
                <th className="text-left py-3 px-2 text-gray-500 font-medium">Tier</th>
                <th className="text-right py-3 px-2 text-gray-500 font-medium">Reward</th>
                <th className="text-left py-3 px-2 text-gray-500 font-medium">Status</th>
                <th className="text-right py-3 px-2 text-gray-500 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {bounties.map((bounty) => {
                const status = STATUS_CONFIG[bounty.status];
                const tier = TIER_CONFIG[bounty.tier];
                return (
                  <tr key={bounty.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors" data-testid={`bounty-row-${bounty.id}`}>
                    <td className="py-3 px-2 text-white font-medium max-w-[200px] truncate">{bounty.title}</td>
                    <td className="py-3 px-2">
                      <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ${tier.color} ${tier.bg}`}>{tier.label}</span>
                    </td>
                    <td className="py-3 px-2 text-right text-[#14F195] font-medium">{bounty.reward.toLocaleString()} {bounty.currency}</td>
                    <td className="py-3 px-2">
                      <span className={`inline-flex items-center gap-1.5 text-xs ${status.textClass}`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${status.dotClass}`} />
                        {status.label}
                      </span>
                    </td>
                    <td className="py-3 px-2 text-right text-gray-400">{formatDate(bounty.completedAt)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
