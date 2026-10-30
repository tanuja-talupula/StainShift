import React from "react";
import { ComparisonRow } from "@/lib/types";

interface Props {
  data: ComparisonRow[];
}

export function AccuracyComparisonChart({ data }: Props) {
  const chartHeight = 300;
  const barWidth = 18;
  const groupSpacing = 42;

  return (
    <div className="bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="font-serif text-lg font-medium text-charcoal-900">Accuracy Across Stain Profiles</h3>
          <p className="text-xs text-charcoal-500 mt-0.5">
            Frozen held-out test cohort ($N = 1,077$ patches). Baseline model collapses under deconvolution and shift; Robust model maintains accuracy.
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#A8A196] inline-block" />
            <span className="text-charcoal-600 font-medium">Standard Baseline</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-[#CC785C] inline-block" />
            <span className="text-charcoal-900 font-semibold">Stain-Robust</span>
          </div>
        </div>
      </div>

      {/* SVG Bar Chart */}
      <div className="w-full overflow-x-auto pb-2">
        <div className="min-w-[640px]">
          <svg
            viewBox={`0 0 ${data.length * (barWidth * 2 + groupSpacing) + 60} ${chartHeight + 60}`}
            className="w-full h-auto overflow-visible"
            role="img"
            aria-label="Accuracy comparison bar chart between baseline and stain-robust models across 8 conditions"
          >
            {/* Horizontal Grid lines */}
            {[0, 25, 50, 75, 100].map((tick) => {
              const y = chartHeight - (tick / 100) * chartHeight + 20;
              return (
                <g key={tick}>
                  <line x1="45" y1={y} x2={data.length * (barWidth * 2 + groupSpacing) + 50} y2={y} stroke="#EDE7DE" strokeDasharray="3 3" />
                  <text x="35" y={y + 4} textAnchor="end" fontSize="10" fill="#8C857B" className="font-mono">
                    {tick}%
                  </text>
                </g>
              );
            })}

            {/* Bars */}
            {data.map((row, idx) => {
              const groupX = 55 + idx * (barWidth * 2 + groupSpacing);
              const bHeight = (row.baseline_accuracy_pct / 100) * chartHeight;
              const rHeight = (row.robust_accuracy_pct / 100) * chartHeight;
              const bY = chartHeight - bHeight + 20;
              const rY = chartHeight - rHeight + 20;

              return (
                <g key={row.condition}>
                  {/* Baseline bar */}
                  <rect
                    x={groupX}
                    y={bY}
                    width={barWidth}
                    height={bHeight}
                    fill="#A8A196"
                    rx="3"
                  />
                  <text
                    x={groupX + barWidth / 2}
                    y={bY - 6}
                    textAnchor="middle"
                    fontSize="9.5"
                    fill="#5A554D"
                    className="font-mono font-medium"
                  >
                    {row.baseline_accuracy_pct.toFixed(1)}%
                  </text>

                  {/* Robust bar */}
                  <rect
                    x={groupX + barWidth + 4}
                    y={rY}
                    width={barWidth}
                    height={rHeight}
                    fill="#CC785C"
                    rx="3"
                  />
                  <text
                    x={groupX + barWidth + 4 + barWidth / 2}
                    y={rY - 6}
                    textAnchor="middle"
                    fontSize="9.5"
                    fill="#9B4E37"
                    className="font-mono font-bold"
                  >
                    {row.robust_accuracy_pct.toFixed(1)}%
                  </text>

                  {/* X-axis Label */}
                  <text
                    x={groupX + barWidth + 2}
                    y={chartHeight + 40}
                    textAnchor="middle"
                    fontSize="10"
                    fill="#3D3A37"
                    className="font-sans font-medium"
                  >
                    {row.condition.replace(/_/g, " ")}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Accessible Table Alternative */}
      <div className="pt-4 border-t border-[#E8E4DD]">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-charcoal-700">
            Tabular Comparison
          </span>
          <span className="text-xs text-charcoal-400 font-mono">Held-Out Test N=1,077</span>
        </div>
        <div className="overflow-x-auto border border-[#E8E4DD] rounded-xl">
          <table className="w-full text-left text-xs text-charcoal-700">
            <thead className="bg-[#FAF8F5] border-b border-[#E8E4DD] text-charcoal-500 font-medium">
              <tr>
                <th scope="col" className="py-2.5 px-3">Condition</th>
                <th scope="col" className="py-2.5 px-3 text-right">Baseline Accuracy</th>
                <th scope="col" className="py-2.5 px-3 text-right">Robust Accuracy</th>
                <th scope="col" className="py-2.5 px-3 text-right">Accuracy Delta</th>
                <th scope="col" className="py-2.5 px-3 text-right">Net Recovery</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E4DD] font-mono text-[11px]">
              {data.map((row) => {
                const delta = row.robust_accuracy_pct - row.baseline_accuracy_pct;
                return (
                  <tr key={row.condition} className="hover:bg-[#FAF8F5] transition">
                    <td className="py-2 px-3 font-sans font-medium text-charcoal-900">{row.condition.replace(/_/g, " ")}</td>
                    <td className="py-2 px-3 text-right text-charcoal-600">{row.baseline_accuracy_pct.toFixed(2)}%</td>
                    <td className="py-2 px-3 text-right font-bold text-[#CC785C]">{row.robust_accuracy_pct.toFixed(2)}%</td>
                    <td className="py-2 px-3 text-right text-charcoal-500">
                      {delta > 0 ? `+${delta.toFixed(2)}%` : `${delta.toFixed(2)}%`}
                    </td>
                    <td className="py-2 px-3 text-right font-bold text-[#2D5A46]">
                      {row.net_recovery_pct > 0 ? `+${row.net_recovery_pct.toFixed(2)}%` : "0.00%"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
