import type { BountySubmission, SubmissionStatus } from '../../types/bountyDetail';

/** Status display colors for submission badges. */
const STATUS_COLOR: Record<SubmissionStatus, string> = {
  pending: 'text-gray-500',
  'in-review': 'text-yellow-400',
  approved: 'text-[#14F195]',
  rejected: 'text-red-400',
};

/** SolFoundry submissions list -- PR submissions with author, status, and GitHub link. */
export function SubmissionsList({ submissions }: { submissions: BountySubmission[] }) {
  return (
    <div data-testid="submissions">
      <h2 className="text-lg font-semibold text-white mb-3">
        Submissions ({submissions.length})
      </h2>
      {submissions.length === 0 ? (
        <p className="text-sm text-gray-500" data-testid="submissions-empty">No submissions yet.</p>
      ) : (
        <ul className="space-y-3">
          {submissions.map((s) => (
            <li key={s.id} className="rounded-lg border border-gray-700 p-3" data-testid={`submission-${s.id}`}>
              <div className="flex justify-between">
                <span className="text-sm text-white">{s.author}</span>
                <span className={'text-xs ' + STATUS_COLOR[s.status]}>{s.status}</span>
              </div>
              <a
                href={s.prUrl}
                className="text-xs text-[#14F195] hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                View PR
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
