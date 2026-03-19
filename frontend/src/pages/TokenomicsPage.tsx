import { Coins, Flame, Lock, Vote, TrendingUp, ArrowDownRight } from "lucide-react";

const tokenDistribution = [
  { label: "Community Rewards", pct: 40, color: "bg-foundry-purple" },
  { label: "Team & Advisors", pct: 15, color: "bg-foundry-green" },
  { label: "Treasury", pct: 20, color: "bg-blue-500" },
  { label: "Liquidity", pct: 15, color: "bg-orange-500" },
  { label: "Public Sale", pct: 10, color: "bg-pink-500" },
];

const mechanisms = [
  {
    icon: Flame,
    title: "Deflationary Burns",
    description:
      "2% of every bounty fee is permanently burned, reducing total supply over time.",
  },
  {
    icon: Lock,
    title: "Staking Rewards",
    description:
      "Stake FORGE to earn yield. Longer lock periods receive higher multipliers (up to 3x).",
  },
  {
    icon: Vote,
    title: "Governance",
    description:
      "FORGE holders vote on platform upgrades, fee structures, and treasury allocations.",
  },
  {
    icon: TrendingUp,
    title: "Reputation Mining",
    description:
      "Complete bounties to earn FORGE. Higher reputation = higher mining rate per bounty.",
  },
  {
    icon: ArrowDownRight,
    title: "Fee Redistribution",
    description:
      "Platform fees (3% of bounty value) are split: 50% to stakers, 30% burned, 20% treasury.",
  },
  {
    icon: Coins,
    title: "Agent Marketplace",
    description:
      "AI agents are priced in FORGE. Running agents creates demand and burns tokens.",
  },
];

export function TokenomicsPage() {
  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">FORGE Tokenomics</h1>
        <p className="text-sm text-foundry-text-muted mt-1">
          The economic engine powering the SolFoundry ecosystem
        </p>
      </div>

      {/* Overview stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 mb-8">
        <div className="card">
          <div className="text-xs text-foundry-text-dim">Total Supply</div>
          <div className="text-xl font-bold mt-1">1,000,000,000</div>
          <div className="text-xs text-foundry-text-dim">FORGE</div>
        </div>
        <div className="card">
          <div className="text-xs text-foundry-text-dim">Circulating</div>
          <div className="text-xl font-bold text-foundry-green mt-1">
            247,500,000
          </div>
          <div className="text-xs text-foundry-text-dim">24.75%</div>
        </div>
        <div className="card">
          <div className="text-xs text-foundry-text-dim">Total Burned</div>
          <div className="text-xl font-bold text-orange-400 mt-1">
            12,340,000
          </div>
          <div className="text-xs text-foundry-text-dim">1.23%</div>
        </div>
        <div className="card">
          <div className="text-xs text-foundry-text-dim">Total Staked</div>
          <div className="text-xl font-bold text-foundry-purple mt-1">
            89,200,000
          </div>
          <div className="text-xs text-foundry-text-dim">36.04% of circ.</div>
        </div>
      </div>

      {/* Distribution */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold mb-6">Token Distribution</h2>

        {/* Bar chart */}
        <div className="flex h-6 rounded-full overflow-hidden mb-6">
          {tokenDistribution.map((item) => (
            <div
              key={item.label}
              className={`${item.color} transition-all duration-500`}
              style={{ width: `${item.pct}%` }}
              title={`${item.label}: ${item.pct}%`}
            />
          ))}
        </div>

        {/* Legend */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {tokenDistribution.map((item) => (
            <div key={item.label} className="flex items-center gap-2">
              <div className={`h-3 w-3 rounded-full ${item.color}`} />
              <div>
                <div className="text-xs font-medium">{item.label}</div>
                <div className="text-xs text-foundry-text-dim">{item.pct}%</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Mechanisms */}
      <h2 className="text-lg font-semibold mb-4">Token Mechanics</h2>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {mechanisms.map((mech) => {
          const Icon = mech.icon;
          return (
            <div key={mech.title} className="card">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-foundry-purple/10 mb-4">
                <Icon size={20} className="text-foundry-purple" />
              </div>
              <h3 className="font-semibold text-sm mb-2">{mech.title}</h3>
              <p className="text-sm text-foundry-text-muted leading-relaxed">
                {mech.description}
              </p>
            </div>
          );
        })}
      </div>

      {/* Staking tiers */}
      <div className="card mt-8">
        <h2 className="text-lg font-semibold mb-4">Staking Tiers</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-foundry-border text-foundry-text-dim">
                <th className="px-4 py-3 text-left font-medium">Duration</th>
                <th className="px-4 py-3 text-right font-medium">
                  Multiplier
                </th>
                <th className="px-4 py-3 text-right font-medium">APY</th>
                <th className="px-4 py-3 text-right font-medium">
                  Voting Power
                </th>
              </tr>
            </thead>
            <tbody>
              {[
                { dur: "30 days", mult: "1.0x", apy: "8%", vote: "1x" },
                { dur: "90 days", mult: "1.5x", apy: "14%", vote: "1.5x" },
                { dur: "180 days", mult: "2.0x", apy: "22%", vote: "2x" },
                { dur: "365 days", mult: "3.0x", apy: "35%", vote: "3x" },
              ].map((tier) => (
                <tr
                  key={tier.dur}
                  className="border-b border-foundry-border last:border-0"
                >
                  <td className="px-4 py-3 font-medium">{tier.dur}</td>
                  <td className="px-4 py-3 text-right text-foundry-purple font-bold">
                    {tier.mult}
                  </td>
                  <td className="px-4 py-3 text-right text-foundry-green font-bold">
                    {tier.apy}
                  </td>
                  <td className="px-4 py-3 text-right">{tier.vote}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
