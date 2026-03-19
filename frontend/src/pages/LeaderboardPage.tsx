import { useState } from "react";
import { Trophy, Medal, Flame, Star } from "lucide-react";

type Period = "all_time" | "monthly" | "weekly";

interface MockEntry {
  rank: number;
  wallet: string;
  username: string;
  reputation: number;
  bounties: number;
  earned: number;
  streak: number;
}

const MOCK_ENTRIES: MockEntry[] = [
  { rank: 1, wallet: "7xKX...3mPq", username: "CryptoForge", reputation: 9850, bounties: 47, earned: 1240, streak: 42 },
  { rank: 2, wallet: "9aBC...xYz1", username: "RustMaster", reputation: 8720, bounties: 38, earned: 980, streak: 28 },
  { rank: 3, wallet: "3dEF...aBc2", username: "SolDev42", reputation: 7450, bounties: 31, earned: 850, streak: 19 },
  { rank: 4, wallet: "5gHI...dEf3", username: "AnchorPro", reputation: 6890, bounties: 26, earned: 720, streak: 14 },
  { rank: 5, wallet: "2jKL...gHi4", username: "TokenWiz", reputation: 5920, bounties: 22, earned: 580, streak: 11 },
  { rank: 6, wallet: "8mNO...jKl5", username: "ChainCoder", reputation: 5100, bounties: 19, earned: 490, streak: 8 },
  { rank: 7, wallet: "4pQR...mNo6", username: "DeFiDev", reputation: 4650, bounties: 16, earned: 410, streak: 5 },
  { rank: 8, wallet: "6sTU...pQr7", username: "BugHunter", reputation: 4200, bounties: 14, earned: 350, streak: 3 },
];

function getRankIcon(rank: number) {
  switch (rank) {
    case 1:
      return <Trophy size={18} className="text-yellow-400" />;
    case 2:
      return <Medal size={18} className="text-gray-300" />;
    case 3:
      return <Medal size={18} className="text-amber-600" />;
    default:
      return (
        <span className="text-sm font-bold text-foundry-text-dim w-[18px] text-center">
          {rank}
        </span>
      );
  }
}

export function LeaderboardPage() {
  const [period, setPeriod] = useState<Period>("all_time");

  return (
    <div className="animate-fade-in">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Leaderboard</h1>
          <p className="text-sm text-foundry-text-muted mt-1">
            Top contributors ranked by reputation
          </p>
        </div>
        <div className="flex gap-1 rounded-lg border border-foundry-border bg-foundry-surface p-1">
          {(["weekly", "monthly", "all_time"] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                period === p
                  ? "bg-foundry-purple text-white"
                  : "text-foundry-text-muted hover:text-foundry-text"
              }`}
            >
              {p === "all_time" ? "All Time" : p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Top 3 podium */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {MOCK_ENTRIES.slice(0, 3).map((entry) => (
          <div
            key={entry.rank}
            className={`card text-center ${
              entry.rank === 1 ? "border-yellow-500/30 glow-purple" : ""
            }`}
          >
            <div className="flex justify-center mb-3">
              {getRankIcon(entry.rank)}
            </div>
            <div className="text-sm font-bold truncate">{entry.username}</div>
            <div className="text-xs text-foundry-text-dim mt-1">
              {entry.wallet}
            </div>
            <div className="mt-3 text-xl font-bold gradient-text-purple">
              {entry.reputation.toLocaleString()}
            </div>
            <div className="text-xs text-foundry-text-dim">reputation</div>
            <div className="mt-3 flex justify-center gap-3 text-xs">
              <span className="text-foundry-green">
                {entry.earned} SOL
              </span>
              <span className="flex items-center gap-1 text-orange-400">
                <Flame size={12} />
                {entry.streak}d
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="card overflow-hidden p-0">
        <table className="w-full">
          <thead>
            <tr className="border-b border-foundry-border text-xs text-foundry-text-dim">
              <th className="px-4 py-3 text-left font-medium">Rank</th>
              <th className="px-4 py-3 text-left font-medium">Contributor</th>
              <th className="px-4 py-3 text-right font-medium">Reputation</th>
              <th className="px-4 py-3 text-right font-medium hidden sm:table-cell">
                Bounties
              </th>
              <th className="px-4 py-3 text-right font-medium hidden md:table-cell">
                Earned
              </th>
              <th className="px-4 py-3 text-right font-medium hidden lg:table-cell">
                Streak
              </th>
            </tr>
          </thead>
          <tbody>
            {MOCK_ENTRIES.map((entry) => (
              <tr
                key={entry.rank}
                className="border-b border-foundry-border last:border-0 hover:bg-foundry-surface/50 transition-colors"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    {getRankIcon(entry.rank)}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-sm">{entry.username}</div>
                  <div className="text-xs text-foundry-text-dim">
                    {entry.wallet}
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Star size={12} className="text-foundry-purple" />
                    <span className="font-bold text-sm">
                      {entry.reputation.toLocaleString()}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right text-sm hidden sm:table-cell">
                  {entry.bounties}
                </td>
                <td className="px-4 py-3 text-right text-sm text-foundry-green hidden md:table-cell">
                  {entry.earned} SOL
                </td>
                <td className="px-4 py-3 text-right hidden lg:table-cell">
                  <span className="inline-flex items-center gap-1 text-sm text-orange-400">
                    <Flame size={12} />
                    {entry.streak}d
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
