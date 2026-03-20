import type { ReputationCategory } from '../../types/profile';

interface ReputationBreakdownProps {
  categories: ReputationCategory[];
  totalScore: number;
}

export function ReputationBreakdown({ categories, totalScore }: ReputationBreakdownProps) {
  const maxPossible = categories.reduce((sum, c) => sum + c.maxPoints, 0);

  return (
    <div className="rounded-xl border border-gray-800 bg-[#111111] p-5" data-testid="reputation-breakdown">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-lg font-semibold text-white">Reputation Breakdown</h3>
          <p className="text-sm text-gray-500">How your reputation score is calculated</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-[#9945FF]" data-testid="reputation-total">
            {totalScore.toLocaleString()}
          </p>
          <p className="text-xs text-gray-500">of {maxPossible.toLocaleString()} max</p>
        </div>
      </div>

      {categories.length === 0 ? (
        <p className="text-gray-500 text-sm py-6 text-center" data-testid="reputation-empty">
          No reputation data available yet.
        </p>
      ) : (
      <div className="space-y-4">
        {categories.map((category) => {
          const percentage = category.maxPoints > 0 ? (category.points / category.maxPoints) * 100 : 0;
          return (
            <div key={category.label} data-testid={`reputation-category-${category.label.toLowerCase().replace(/\s+/g, '-')}`}>
              <div className="flex items-center justify-between mb-1.5">
                <div>
                  <span className="text-sm font-medium text-white">{category.label}</span>
                  <p className="text-xs text-gray-500">{category.description}</p>
                </div>
                <span className="text-sm font-semibold text-gray-300 whitespace-nowrap ml-4">
                  {category.points} / {category.maxPoints}
                </span>
              </div>
              <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[#9945FF] to-[#14F195] transition-all duration-500"
                  style={{ width: `${Math.min(percentage, 100)}%` }}
                  role="progressbar"
                  aria-valuenow={category.points}
                  aria-valuemin={0}
                  aria-valuemax={category.maxPoints}
                  aria-label={`${category.label}: ${category.points} of ${category.maxPoints}`}
                />
              </div>
            </div>
          );
        })}
      </div>
      )}

      {maxPossible > 0 && (
      <div className="mt-6 pt-4 border-t border-gray-800">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-400">Overall Progress</span>
          <span className="text-sm font-semibold text-white">
            {Math.round((totalScore / maxPossible) * 100)}%
          </span>
        </div>
        <div className="h-3 rounded-full bg-gray-800 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#9945FF] via-purple-500 to-[#14F195] transition-all duration-500"
            style={{ width: `${Math.min((totalScore / maxPossible) * 100, 100)}%` }}
            role="progressbar"
            aria-valuenow={totalScore}
            aria-valuemin={0}
            aria-valuemax={maxPossible}
            aria-label={`Overall reputation: ${totalScore} of ${maxPossible}`}
          />
        </div>
      </div>
      )}
    </div>
  );
}
