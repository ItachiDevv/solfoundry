import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Clock,
  User,
  Tag,
  ExternalLink,
  MessageSquare,
  GitPullRequest,
} from "lucide-react";

export function BountyDetailPage() {
  const { id } = useParams<{ id: string }>();

  // Placeholder - will be replaced with API call using id
  return (
    <div className="animate-fade-in max-w-4xl">
      <Link
        to="/bounties"
        className="inline-flex items-center gap-2 text-sm text-foundry-text-muted hover:text-foundry-text transition-colors mb-6"
      >
        <ArrowLeft size={16} />
        Back to Bounties
      </Link>

      {/* Header */}
      <div className="card mb-6">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className="badge border bg-foundry-green/15 text-foundry-green border-foundry-green/25">
            open
          </span>
          <span className="badge border bg-orange-500/15 text-orange-400 border-orange-500/25">
            advanced
          </span>
          <span className="text-xs text-foundry-text-dim">
            Bounty #{id}
          </span>
        </div>

        <h1 className="text-2xl font-bold mb-2">
          Implement token staking contract
        </h1>
        <p className="text-foundry-text-muted leading-relaxed">
          Build the FORGE token staking mechanism with time-locked rewards.
          Contributors can stake their FORGE tokens and earn yield based on
          lock duration and platform activity.
        </p>

        <div className="mt-6 flex flex-wrap gap-6 text-sm">
          <div className="flex items-center gap-2 text-foundry-text-muted">
            <User size={14} />
            <span>Posted by 7xKX...3mPq</span>
          </div>
          <div className="flex items-center gap-2 text-foundry-text-muted">
            <Clock size={14} />
            <span>Deadline: Apr 15, 2026</span>
          </div>
          <div className="flex items-center gap-2 text-foundry-text-muted">
            <Tag size={14} />
            <span>rust, anchor, defi</span>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-4">
          <div className="rounded-lg border border-foundry-green/25 bg-foundry-green/5 px-4 py-3">
            <div className="text-xs text-foundry-text-dim">Reward</div>
            <div className="text-xl font-bold text-foundry-green">50 SOL</div>
          </div>
          <div className="rounded-lg border border-foundry-border bg-foundry-surface px-4 py-3">
            <div className="text-xs text-foundry-text-dim">Submissions</div>
            <div className="text-xl font-bold text-foundry-text">3</div>
          </div>
          <div className="rounded-lg border border-foundry-border bg-foundry-surface px-4 py-3">
            <div className="text-xs text-foundry-text-dim">Escrow</div>
            <div className="text-xl font-bold text-foundry-purple">Funded</div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 mb-6">
        <button className="btn-primary">Claim Bounty</button>
        <button className="btn-secondary inline-flex items-center gap-2">
          <MessageSquare size={14} />
          Discuss
        </button>
        <button className="btn-secondary inline-flex items-center gap-2">
          <ExternalLink size={14} />
          View on Explorer
        </button>
      </div>

      {/* Description */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold mb-4">Requirements</h2>
        <div className="prose prose-invert prose-sm max-w-none text-foundry-text-muted">
          <ul className="space-y-2 list-disc list-inside">
            <li>Anchor program for FORGE token staking</li>
            <li>Support for multiple lock periods (30, 90, 180, 365 days)</li>
            <li>
              Yield calculation based on lock duration multiplier and pool share
            </li>
            <li>Emergency unstake with penalty (50% of accrued rewards)</li>
            <li>Admin functions for pool configuration</li>
            <li>Full test suite with &gt;90% coverage</li>
            <li>IDL and TypeScript client generation</li>
          </ul>
        </div>
      </div>

      {/* Submissions */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Submissions</h2>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-lg border border-foundry-border bg-foundry-bg p-4"
            >
              <div className="flex items-center gap-3">
                <GitPullRequest size={16} className="text-foundry-purple" />
                <div>
                  <div className="text-sm font-medium">
                    Contributor {i}xAB...cD{i}
                  </div>
                  <div className="text-xs text-foundry-text-dim">
                    Submitted 2 days ago
                  </div>
                </div>
              </div>
              <span className="badge border bg-yellow-500/15 text-yellow-400 border-yellow-500/25">
                pending
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
