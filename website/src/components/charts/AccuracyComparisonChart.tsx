import React from "react";
import { ComparisonRow } from "@/lib/types";

interface Props {
  data: ComparisonRow[];
}

export function AccuracyComparisonChart({ data }: Props) {
  // Chart dimensions
  const chartHeight = 300;
  const barWidth = 18;
  const groupSpacing = 42;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-slate-900">Accuracy Across Stain Profiles</h3>
          <p className="text-xs text-slate-500">
            Frozen held-out test cohort ($N = 1,077$ patches). Baseline model collapses under deconvolution and shift; Robust model maintains accuracy.
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-slate-400 inline-block" />
            <span className="text-slate-600 font-medium">Standard Baseline</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-brand-600 inline-block" />
            <span className="text-slate-900 font-semibold">Stain-Robust Model</span>
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
                  <line x1="45" y1={y} x2={data.length * (barWidth * 2 + groupSpacing) + 50} y2={y} stroke="#e2e8f0" strokeDasharray="3 3" />
                  <text x="35" y={y + 4} textAnchor="end" fontSize="10" fill="#64748b" className="font-mono">
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
              const isReconstruction = row.condition === "reconstruction_only";

              return (
                <g key={row.condition} className="group">
                  {/* Highlight box for reconstruction control */}
                  {isReconstruction && (
                    <rect
                      x={groupX - 6}
                      y="15"
                      width={barWidth * 2 + 12}
                      height={chartHeight + 10}
                      fill="#fef2f2"
                      rx="4"
                      className="opacity-75"
                    />
                  )}

                  {/* Baseline bar */}
                  <rect
                    x={groupX}
                    y={bY}
                    width={barWidth}
                    height={bHeight}
                    fill={isReconstruction ? "#ef4444" : "#94a3b8"}
                    rx="2"
                    className="transition hover:opacity-80"
                  />
                  <text x={groupX + barWidth / 2} y={bY - 4} textAnchor="middle" fontSize="9" fill="#475569" className="font-mono font-medium">
                    {row.baseline_accuracy_pct.toFixed(1)}%
                  </text>

                  {/* Robust bar */}
                  <rect
                    x={groupX + barWidth + 2}
                    y={rY}
                    width={barWidth}
                    height={rHeight}
                    fill="#0284c7"
                    rx="2"
                    className="transition hover:opacity-80"
                  />
                  <text x={groupX + barWidth + 2 + barWidth / 2} y={rY - 4} textAnchor="middle" fontSize="9" fill="#0369a1" className="font-mono font-bold">
                    {row.robust_accuracy_pct.toFixed(1)}%
                  </text>

                  {/* X axis condition label */}
                  <text
                    x={groupX + barWidth}
                    y={chartHeight + 36}
                    textAnchor="middle"
                    fontSize="10"
                    fill="#334155"
                    className="font-medium"
                  >
                    {row.condition.replace(/_/g, " ")}
                  </text>

                  {/* Reconstruction callout flag */}
                  {isReconstruction && (
                    <text x={groupX + barWidth} y={chartHeight + 50} textAnchor="middle" fontSize="8.5" fill="#dc2626" className="font-bold">
                      Control (-66.0%)
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Accessible HTML Table Fallback */}
      <div className="border-t border-slate-100 pt-4">
        <details className="group">
          <summary className="text-xs text-slate-500 hover:text-slate-800 cursor-pointer font-medium select-none">
            View Accessible Data Table
          </summary>
          <div className="overflow-x-auto mt-3">
            <table className="w-full text-xs text-left text-slate-700">
              <thead className="bg-slate-50 text-slate-900 font-semibold border-b border-slate-200">
                <tr>
                  <th scope="col" className="py-2 px-3">Stain Condition</th>
                  <th scope="col" className="py-2 px-3">Condition Description</th>
                  <th scope="col" className="py-2 px-3 text-right">Baseline Accuracy</th>
                  <th scope="col" className="py-2 px-3 text-right">Robust Accuracy</th>
                  <th scope="col" className="py-2 px-3 text-right">Net Recovery</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.map((row) => (
                  <tr key={row.condition} className="hover:bg-slate-50/50">
                    <td className="py-2 px-3 font-mono font-medium">{row.condition}</td>
                    <td className="py-2 px-3 text-slate-500">{row.description}</td>
                    <td className="py-2 px-3 text-right font-mono">{row.baseline_accuracy_pct.toFixed(2)}%</td>
                    <td className="py-2 px-3 text-right font-mono font-semibold text-brand-700">{row.robust_accuracy_pct.toFixed(2)}%</td>
                    <td className="py-2 px-3 text-right font-mono text-emerald-600 font-medium">
                      {row.net_recovery_pct > 0 ? `+${row.net_recovery_pct.toFixed(2)}%` : `${row.net_recovery_pct.toFixed(2)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </div>
    </div>
  );
}
