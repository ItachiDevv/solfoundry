import type { BountyDetail } from '../../types/bountyDetail';

/** Tier badge color mapping. */
const TIER: Record<string, string> = {
  T1: 'bg-[#14F195]/15 text-[#14F195]',
  T2: 'bg-[#FFD700]/15 text-[#FFD700]',
  T3: 'bg-[#FF6B6B]/15 text-[#FF6B6B]',
};

/** SolFoundry bounty header -- title, tier badge, reward, and project name. */
export function BountyHeader({ bounty: b }: { bounty: BountyDetail }) {
  return (
    <div data-testid="bounty-header">
      <div className="flex items-center gap-3 mb-2">
        <span className={'rounded-md px-2 py-0.5 text-xs font-bold ' + TIER[b.tier]}>{b.tier}</span>
        <span className="text-xs text-gray-500">{b.projectName}</span>
      </div>
      <h1 className="text-2xl font-bold text-white mb-3" data-testid="bounty-title">{b.title}</h1>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold text-[#14F195]" data-testid="bounty-reward">
          {b.rewardAmount.toLocaleString()}
        </span>
        <span className="text-sm text-gray-500">{b.currency}</span>
      </div>
    </div>
  );
}
