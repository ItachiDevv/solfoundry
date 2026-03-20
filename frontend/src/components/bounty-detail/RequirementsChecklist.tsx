import type { BountyRequirement } from '../../types/bountyDetail';

/** SolFoundry requirements checklist with completed/pending indicators. */
export function RequirementsChecklist({ requirements }: { requirements: BountyRequirement[] }) {
  return (
    <div data-testid="requirements">
      <h2 className="text-lg font-semibold text-white mb-3">Requirements</h2>
      {requirements.length === 0 ? (
        <p className="text-sm text-gray-500" data-testid="requirements-empty">No requirements specified.</p>
      ) : (
        <ul className="space-y-2">
          {requirements.map((r, i) => (
            <li key={i} className="flex items-center gap-2 text-sm">
              <span className={r.completed ? 'text-[#14F195]' : 'text-gray-500'}>
                {r.completed ? '[x]' : '[ ]'}
              </span>
              <span className={r.completed ? 'text-gray-400 line-through' : 'text-white'}>
                {r.text}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
