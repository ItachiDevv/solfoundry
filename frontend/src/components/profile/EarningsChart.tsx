import { useMemo } from 'react';
import type { MonthlyEarning } from '../../types/profile';

interface EarningsChartProps {
  data: MonthlyEarning[];
}

const CHART_HEIGHT = 220;
const BAR_GAP = 8;
const CHART_PADDING = { top: 20, right: 16, bottom: 40, left: 55 };

export function EarningsChart({ data }: EarningsChartProps) {
  const { bars, totalEarnings, gridLines, viewBoxWidth } = useMemo(() => {
    if (data.length === 0) {
      return { bars: [], totalEarnings: 0, gridLines: [], viewBoxWidth: 600 };
    }

    const amounts = data.map((d) => d.amount);
    const max = Math.max(...amounts, 1);
    const total = amounts.reduce((sum, a) => sum + a, 0);

    const vbWidth = 600;
    const drawLeft = CHART_PADDING.left;
    const drawRight = vbWidth - CHART_PADDING.right;
    const drawTop = CHART_PADDING.top;
    const drawBottom = CHART_HEIGHT - CHART_PADDING.bottom;
    const drawWidth = drawRight - drawLeft;
    const drawHeight = drawBottom - drawTop;

    const barWidth = (drawWidth - BAR_GAP * (data.length - 1)) / data.length;

    const barData = data.map((d, i) => {
      const barHeight = (d.amount / max) * drawHeight;
      const x = drawLeft + i * (barWidth + BAR_GAP);
      const y = drawBottom - barHeight;
      return { x, y, width: barWidth, height: barHeight, month: d.month, amount: d.amount };
    });

    const lines = Array.from({ length: 4 }, (_, i) => {
      const value = Math.round((max / 4) * (i + 1));
      const y = drawTop + drawHeight - (value / max) * drawHeight;
      return { y, label: `$${(value / 1000).toFixed(1)}k` };
    });

    return { bars: barData, totalEarnings: total, gridLines: lines, viewBoxWidth: vbWidth };
  }, [data]);

  return (
    <div className="rounded-xl border border-gray-800 bg-[#111111] p-5" data-testid="profile-earnings-chart">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Earnings</h3>
          <p className="text-sm text-gray-500">Monthly breakdown</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-[#14F195]" data-testid="earnings-total">
            ${totalEarnings.toLocaleString()}
          </p>
          <p className="text-xs text-gray-500">total earned</p>
        </div>
      </div>

      {data.length === 0 ? (
        <div className="flex items-center justify-center h-[220px] text-gray-500 text-sm" data-testid="earnings-empty">
          No earnings data available
        </div>
      ) : (
        <svg
          viewBox={`0 0 ${viewBoxWidth} ${CHART_HEIGHT}`}
          className="w-full h-auto"
          role="img"
          aria-label={`Bar chart showing monthly earnings totaling $${totalEarnings.toLocaleString()}`}
        >
          <defs>
            <linearGradient id="profileBarGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#9945FF" />
              <stop offset="100%" stopColor="#14F195" />
            </linearGradient>
          </defs>

          {gridLines.map((line) => (
            <g key={line.label}>
              <line x1={CHART_PADDING.left} y1={line.y} x2={viewBoxWidth - CHART_PADDING.right} y2={line.y} stroke="#222222" strokeWidth={1} strokeDasharray="4 4" />
              <text x={CHART_PADDING.left - 8} y={line.y + 4} textAnchor="end" fill="#666666" fontSize={10}>{line.label}</text>
            </g>
          ))}

          {bars.map((bar) => (
            <g key={bar.month} data-testid={`earnings-bar-${bar.month}`}>
              <rect x={bar.x} y={bar.y} width={bar.width} height={bar.height} rx={4} fill="url(#profileBarGradient)" opacity={0.85} className="transition-opacity hover:opacity-100" />
              {bar.amount > 0 && (
                <text x={bar.x + bar.width / 2} y={bar.y - 6} textAnchor="middle" fill="#9945FF" fontSize={9} fontWeight="bold">
                  ${(bar.amount / 1000).toFixed(1)}k
                </text>
              )}
              <text x={bar.x + bar.width / 2} y={CHART_HEIGHT - 10} textAnchor="middle" fill="#666666" fontSize={9}>
                {bar.month.split(' ')[0]}
              </text>
            </g>
          ))}
        </svg>
      )}
    </div>
  );
}
