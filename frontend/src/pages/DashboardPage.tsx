import { Link } from "react-router-dom";
import {
  Target,
  CheckCircle,
  Clock,
  Coins,
  Star,
  Flame,
  ArrowRight,
  TrendingUp,
} from "lucide-react";
import { useAuth } from "../providers/AuthProvider";

const stats = [
  {
    label: "Active Bounties",
    value: "3",
    icon: Target,
    color: "text-foundry-purple",
  },
  {
    label: "Completed",
    value: "12",
    icon: CheckCircle,
    color: "text-foundry-green",
  },
  {
    label: "In Review",
    value: "2",
    icon: Clock,
    color: "text-yellow-400",
  },
  {
    label: "Total Earned",
    value: "142 SOL",
    icon: Coins,
    color: "text-foundry-green",
  },
];

const recentBounties = [
  {
    id: "1",
    title: "Implement token staking contract",
    status: "in_progress",
    reward: "50 SOL",
    deadline: "Apr 15, 2026",
  },
  {
    id: "2",
    title: "Fix escrow timeout bug",
    status: "review",
    reward: "15 SOL",
    deadline: "Mar 22, 2026",
  },
  {
    id: "3",
    title: "Write integration tests for bounty API",
    status: "in_progress",
    reward: "20 SOL",
    deadline: "Mar 30, 2026",
  },
];

const statusBadge: Record<string, string> = {
  in_progress: "bg-foundry-purple/15 text-foundry-purple border-foundry-purple/25",
  review: "bg-yellow-500/15 text-yellow-400 border-yellow-500/25",
  completed: "bg-foundry-green/15 text-foundry-green border-foundry-green/25",
};

export function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="animate-fade-in">
      {/* Welcome */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold">
          Welcome back,{" "}
          <span className="gradient-text-purple">
            {user?.username ?? "Contributor"}
          </span>
        </h1>
        <p className="text-sm text-foundry-text-muted mt-1">
          Here&apos;s your activity overview
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="card">
              <div className="flex items-center justify-between mb-3">
                <Icon size={18} className={stat.color} />
                <TrendingUp size={14} className="text-foundry-text-dim" />
              </div>
              <div className="text-2xl font-bold">{stat.value}</div>
              <div className="text-xs text-foundry-text-dim mt-1">
                {stat.label}
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent bounties */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Your Bounties</h2>
            <Link
              to="/bounties"
              className="text-sm text-foundry-purple hover:text-foundry-purple-light transition-colors inline-flex items-center gap-1"
            >
              View All <ArrowRight size={14} />
            </Link>
          </div>
          <div className="space-y-3">
            {recentBounties.map((bounty) => (
              <Link
                key={bounty.id}
                to={`/bounties/${bounty.id}`}
                className="card-interactive flex items-center justify-between"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`badge border ${statusBadge[bounty.status]}`}
                    >
                      {bounty.status.replace("_", " ")}
                    </span>
                  </div>
                  <h3 className="font-medium text-sm truncate">
                    {bounty.title}
                  </h3>
                  <span className="text-xs text-foundry-text-dim">
                    Due {bounty.deadline}
                  </span>
                </div>
                <div className="text-sm font-bold text-foundry-green ml-4 shrink-0">
                  {bounty.reward}
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Reputation card */}
        <div>
          <h2 className="text-lg font-semibold mb-4">Your Reputation</h2>
          <div className="card">
            <div className="text-center mb-6">
              <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-foundry-purple/10 mb-3">
                <Star size={28} className="text-foundry-purple" />
              </div>
              <div className="text-3xl font-bold gradient-text-purple">
                {user?.reputation?.toLocaleString() ?? "4,520"}
              </div>
              <div className="text-xs text-foundry-text-dim mt-1">
                Reputation Score
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-foundry-text-muted">Current Streak</span>
                <span className="flex items-center gap-1 text-orange-400 font-medium">
                  <Flame size={14} />
                  14 days
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-foundry-text-muted">Global Rank</span>
                <span className="font-medium">#42</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-foundry-text-muted">Badges</span>
                <span className="font-medium">7</span>
              </div>
            </div>

            <Link
              to="/leaderboard"
              className="btn-secondary w-full mt-6 text-center block"
            >
              View Leaderboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
