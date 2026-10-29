import React from "react";
import { ComparisonRow } from "@/lib/types";

interface Props {
  data: ComparisonRow[];
}

export function AccuracyDropChart({ data }: Props) {
  // Only non-original conditions show drop
  const nonOriginal = data.filter((d) => d.condition !== "original");
  const chartHeight = 260;
  const maxDrop = 80; // 0 to -80%

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-900">Accuracy Drop Relative to Original (Percentage Points)</h3>
        <p className="text-xs text-slate-500">
          Drop calculated as (Acc_condition - Acc_original) * 100. Lower bars represent greater degradation.
        </p>
      </div>

      <div className="w-full overflow-x-auto pb-2">
        <div className="min-w-[560px]">
          <svg viewBox="0 0 560 260" className="w-full h-auto overflow-visible" role="img" aria-label="Accuracy drop in percentage points">
            {/* Zero line at top */}
            <line x1="120" y1="20" x2="540" y2="20" stroke="#94a3b8" strokeWidth="1.5" />
            <text x="110" y="24" textAnchor="end" fontSize="10" fill="#475569" className="font-mono">
              0.0 pp
            </text>

            {/* Grid lines */}
            {[20, 40, 60, 80].map((drop) => {
              const y = 20 + (drop / maxDrop) * (chartHeight - 40);
              return (
                <g key={drop}>
                  <line x1="120" y1={y} x2="540" y2={y} stroke="#e2e8f0" strokeDasharray="3 3" />
                  <text x="110" y={y + 3} textAnchor="end" fontSize="10" fill="#94a3b8" className="font-mono">
                    -{drop} pp
                  </text>
                </g>
              );
            })}

            {/* Bars */}
            {nonOriginal.map((row, idx) => {
              const rowWidth = 40;
              const x = 140 + idx * 56;
              const bHeight = (Math.abs(row.baseline_drop_pct) / maxDrop) * (chartHeight - 40);
              const rHeight = (Math.abs(row.robust_drop_pct) / maxDrop) * (chartHeight - 40);

              return (
                <g key={row.condition}>
                  {/* Baseline drop bar (pointing downward) */}
                  <rect x={x} y="20" width="16" height={bHeight} fill="#f87171" rx="2" />
                  <text x={x + 8} y={20 + bHeight + 12} textAnchor="middle" fontSize="9" fill="#dc2626" className="font-mono font-medium">
                    {row.baseline_drop_pct.toFixed(1)}%
                  </text>

                  {/* Robust drop bar */}
                  <rect x={x + 18} y="20" width="16" height={Math.max(rHeight, 2)} fill="#0284c7" rx="2" />
                  <text x={x + 26} y={20 + Math.max(rHeight, 2) + 12} textAnchor="middle" fontSize="9" fill="#0369a1" className="font-mono font-bold">
                    {row.robust_drop_pct.toFixed(1)}%
                  </text>

                  {/* Label */}
                  <text
                    x={x + 17}
                    y="245"
                    textAnchor="middle"
                    fontSize="9"
                    fill="#334155"
                    className="font-medium"
                  >
                    {row.condition.replace(/synthetic_|heavy_/g, "")}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>
    </div>
  );
}
