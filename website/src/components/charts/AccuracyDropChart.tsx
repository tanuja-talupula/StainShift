import React from "react";
import { ComparisonRow } from "@/lib/types";

interface Props {
  data: ComparisonRow[];
}

export function AccuracyDropChart({ data }: Props) {
  const nonOriginal = data.filter((d) => d.condition !== "original");
  const chartHeight = 260;
  const maxDrop = 80;

  return (
    <div className="bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-sm space-y-6">
      <div>
        <h3 className="font-serif text-lg font-medium text-charcoal-900">Accuracy Drop Relative to Original</h3>
        <p className="text-xs text-charcoal-500 mt-0.5">
          Drop calculated in percentage points relative to unperturbed H&E. Lower bars represent severe degradation.
        </p>
      </div>

      <div className="w-full overflow-x-auto pb-2">
        <div className="min-w-[560px]">
          <svg viewBox="0 0 560 260" className="w-full h-auto overflow-visible" role="img" aria-label="Accuracy drop in percentage points">
            {/* Zero line at top */}
            <line x1="120" y1="20" x2="540" y2="20" stroke="#7A756D" strokeWidth="1.5" />
            <text x="110" y="24" textAnchor="end" fontSize="10" fill="#3D3A37" className="font-mono">
              0.0 pp
            </text>

            {/* Grid lines */}
            {[20, 40, 60, 80].map((drop) => {
              const y = 20 + (drop / maxDrop) * (chartHeight - 40);
              return (
                <g key={drop}>
                  <line x1="120" y1={y} x2="540" y2={y} stroke="#EDE7DE" strokeDasharray="3 3" />
                  <text x="110" y={y + 3} textAnchor="end" fontSize="10" fill="#8C857B" className="font-mono">
                    -{drop} pp
                  </text>
                </g>
              );
            })}

            {/* Bars */}
            {nonOriginal.map((row, idx) => {
              const x = 140 + idx * 56;
              const bHeight = (Math.abs(row.baseline_drop_pct) / maxDrop) * (chartHeight - 40);
              const rHeight = (Math.abs(row.robust_drop_pct) / maxDrop) * (chartHeight - 40);

              return (
                <g key={row.condition}>
                  {/* Baseline drop bar */}
                  <rect x={x} y="20" width="16" height={bHeight} fill="#D47363" rx="3" />
                  <text x={x + 8} y={20 + bHeight + 12} textAnchor="middle" fontSize="9" fill="#9B2A2A" className="font-mono font-medium">
                    {row.baseline_drop_pct.toFixed(1)}%
                  </text>

                  {/* Robust drop bar */}
                  <rect x={x + 18} y="20" width="16" height={rHeight} fill="#CC785C" rx="3" />
                  <text x={x + 26} y={20 + rHeight + 12} textAnchor="middle" fontSize="9" fill="#7D3B29" className="font-mono font-bold">
                    {row.robust_drop_pct.toFixed(1)}%
                  </text>

                  {/* Condition label */}
                  <text x={x + 17} y={chartHeight + 15} textAnchor="middle" fontSize="8.5" fill="#5A554D" className="font-sans">
                    {row.condition.replace(/_/g, " ").slice(0, 10)}
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
