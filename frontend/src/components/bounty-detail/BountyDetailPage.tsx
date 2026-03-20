import { useState } from 'react';
import { useBountyDetail } from '../../hooks/useBountyDetail';
import { BountyHeader } from './BountyHeader';
import { RequirementsChecklist } from './RequirementsChecklist';
import { SubmissionsList } from './SubmissionsList';

/**
 * SolFoundry Bounty Detail Page -- fetches and renders bounty detail
 * with header, description, requirements, submissions, and skills.
 * Dark theme (#0a0a0a), no backend claiming -- CTAs are callback props.
 */
export function BountyDetailPage({ bountyId }: { bountyId: string }) {
  const { bounty, loading, error } = useBountyDetail(bountyId);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-gray-100" data-testid="bounty-detail-page">
      <div className="mx-auto max-w-4xl px-4 py-8">
        {loading && <p className="text-gray-500" data-testid="loading">Loading...</p>}
        {error && <p className="text-red-400" data-testid="error">{error}</p>}
        {bounty && (
          <>
            <BountyHeader bounty={bounty} />
            <div className="mt-6 prose prose-invert max-w-none" data-testid="description">
              <p className="text-sm text-gray-300 whitespace-pre-wrap">{bounty.description}</p>
            </div>
            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <RequirementsChecklist requirements={bounty.requirements} />
              <SubmissionsList submissions={bounty.submissions} />
            </div>
            {bounty.skills.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-1" data-testid="skills">
                {bounty.skills.map((s) => (
                  <span key={s} className="rounded-md bg-gray-800 px-2 py-0.5 text-xs text-gray-400">
                    {s}
                  </span>
                ))}
              </div>
            )}
            <footer className="mt-8 pt-4 border-t border-gray-800 text-center">
              <p className="text-xs text-gray-600">
                <span className="text-[#9945FF] font-semibold">SolFoundry</span>
                {' '}&mdash; Decentralized bounty platform on Solana
              </p>
            </footer>
          </>
        )}
      </div>
    </div>
  );
}
