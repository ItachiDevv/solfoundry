import type { BountySubmission } from '../../types/bountyDetail';
const STATUS_COLOR: Record<string, string> = { unclaimed: 'text-gray-500', claimed: 'text-blue-400', 'in-review': 'text-yellow-400', approved: 'text-solana-green', rejected: 'text-red-400' };
export function SubmissionsList({ submissions }: { submissions: BountySubmission[] }) {
  return (
    <div data-testid="submissions">
      <h2 className="text-lg font-semibold text-white mb-3">Submissions ({submissions.length})</h2>
      {submissions.length === 0 ? <p className="text-sm text-gray-500">No submissions yet.</p> :
      <ul className="space-y-3">{submissions.map(s => (
        <li key={s.id} className="rounded-lg border border-surface-300 p-3">
          <div className="flex justify-between"><span className="text-sm text-white">{s.author}</span><span className={'text-xs ' + (STATUS_COLOR[s.status] || 'text-gray-500')}>{s.status}</span></div>
          <a href={s.prUrl} className="text-xs text-solana-green hover:underline" target="_blank" rel="noopener">View PR</a>
        </li>))}</ul>}
    </div>);
}
