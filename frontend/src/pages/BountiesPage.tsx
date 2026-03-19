import { useState } from "react";
import { Link } from "react-router-dom";
import { Search, Filter, PlusCircle, ArrowUpDown } from "lucide-react";
import type { Bounty } from "../api/bounties";

// Placeholder bounty data - will be replaced by API calls
const MOCK_BOUNTIES: Bounty[] = [
  {
    id: "1",
    title: "Implement token staking contract",
    description: "Build the FORGE token staking mechanism with time-locked rewards",
    reward_amount: 50,
    reward_token: "SOL",
    status: "open",
    difficulty: "advanced",
    tags: ["rust", "anchor", "defi"],
    creator_wallet: "7xKX...3mPq",
    assignee_wallet: null,
    escrow_address: null,
    created_at: "2026-03-15T10:00:00Z",
    updated_at: "2026-03-15T10:00:00Z",
    deadline: "2026-04-15T10:00:00Z",
    submissions_count: 3,
  },
  {
    id: "2",
    title: "Create leaderboard UI components",
    description: "Build React components for the contributor leaderboard with rankings",
    reward_amount: 15,
    reward_token: "SOL",
    status: "open",
    difficulty: "intermediate",
    tags: ["react", "typescript", "tailwind"],
    creator_wallet: "9aBC...xYz1",
    assignee_wallet: null,
    escrow_address: null,
    created_at: "2026-03-14T08:00:00Z",
    updated_at: "2026-03-14T08:00:00Z",
    deadline: null,
    submissions_count: 1,
  },
  {
    id: "3",
    title: "Add wallet authentication flow",
    description: "Implement sign-in with Solana wallet using message signing",
    reward_amount: 20,
    reward_token: "SOL",
    status: "in_progress",
    difficulty: "intermediate",
    tags: ["solana", "auth", "typescript"],
    creator_wallet: "3dEF...aBc2",
    assignee_wallet: "5gHI...dEf3",
    escrow_address: "EscR...ow12",
    created_at: "2026-03-12T14:00:00Z",
    updated_at: "2026-03-16T09:00:00Z",
    deadline: "2026-03-25T14:00:00Z",
    submissions_count: 0,
  },
];

const difficultyColors: Record<string, string> = {
  beginner: "bg-green-500/15 text-green-400 border-green-500/25",
  intermediate: "bg-yellow-500/15 text-yellow-400 border-yellow-500/25",
  advanced: "bg-orange-500/15 text-orange-400 border-orange-500/25",
  expert: "bg-red-500/15 text-red-400 border-red-500/25",
};

const statusColors: Record<string, string> = {
  open: "bg-foundry-green/15 text-foundry-green border-foundry-green/25",
  in_progress: "bg-foundry-purple/15 text-foundry-purple border-foundry-purple/25",
  review: "bg-yellow-500/15 text-yellow-400 border-yellow-500/25",
  completed: "bg-blue-500/15 text-blue-400 border-blue-500/25",
  cancelled: "bg-red-500/15 text-red-400 border-red-500/25",
};

export function BountiesPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filtered = MOCK_BOUNTIES.filter((b) => {
    const matchesSearch =
      !search ||
      b.title.toLowerCase().includes(search.toLowerCase()) ||
      b.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()));
    const matchesStatus =
      statusFilter === "all" || b.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="animate-fade-in">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Bounty Board</h1>
          <p className="text-sm text-foundry-text-muted mt-1">
            Browse open bounties and start earning
          </p>
        </div>
        <Link
          to="/bounties/create"
          className="btn-primary inline-flex items-center gap-2 self-start"
        >
          <PlusCircle size={16} />
          Create Bounty
        </Link>
      </div>

      {/* Filters */}
      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-foundry-text-dim"
          />
          <input
            type="text"
            placeholder="Search bounties or tags..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-field w-full pl-10"
          />
        </div>
        <div className="flex gap-2">
          <div className="relative">
            <Filter
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-foundry-text-dim pointer-events-none"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input-field appearance-none pl-10 pr-8"
            >
              <option value="all">All Status</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="review">In Review</option>
              <option value="completed">Completed</option>
            </select>
          </div>
          <button className="btn-secondary inline-flex items-center gap-2">
            <ArrowUpDown size={14} />
            Sort
          </button>
        </div>
      </div>

      {/* Bounty list */}
      <div className="mt-6 space-y-3">
        {filtered.map((bounty) => (
          <Link
            key={bounty.id}
            to={`/bounties/${bounty.id}`}
            className="card-interactive flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span
                  className={`badge border ${statusColors[bounty.status]}`}
                >
                  {bounty.status.replace("_", " ")}
                </span>
                <span
                  className={`badge border ${difficultyColors[bounty.difficulty]}`}
                >
                  {bounty.difficulty}
                </span>
              </div>
              <h3 className="font-semibold text-foundry-text truncate">
                {bounty.title}
              </h3>
              <p className="text-sm text-foundry-text-muted mt-1 line-clamp-1">
                {bounty.description}
              </p>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {bounty.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded bg-foundry-surface px-2 py-0.5 text-[11px] text-foundry-text-dim border border-foundry-border"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-6 sm:text-right">
              <div>
                <div className="text-lg font-bold text-foundry-green">
                  {bounty.reward_amount} {bounty.reward_token}
                </div>
                <div className="text-xs text-foundry-text-dim">
                  {bounty.submissions_count} submissions
                </div>
              </div>
            </div>
          </Link>
        ))}

        {filtered.length === 0 && (
          <div className="card text-center py-12">
            <p className="text-foundry-text-muted">
              No bounties found matching your criteria.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
