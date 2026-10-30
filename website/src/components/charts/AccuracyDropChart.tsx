import React from "react";
import { ComparisonRow } from "@/lib/types";

interface Props {
  data: ComparisonRow[];
}

const SHORT_NAMES: Record<string, string> = {
  reconstruction_only: "Deconv Only",
  heavy_hematoxylin: "Heavy Hem.",
  heavy_eosin: "Heavy Eosin",
  pale_understained: "Pale Under.",
  dark_overstained: "Dark Over.",
  synthetic_warm_shift: "Warm Shift",
  synthetic_cool_shift: "Cool Shift",
};

export function AccuracyDropChart({ data }: Props) {
  const nonOriginal = data.filter((d) => d.condition !== "original");
  const chartHeight = 180;
  const maxDrop = 80;

  return (
    <div className="bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-sm space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div>
          <h3 className="font-serif text-lg font-medium text-charcoal-900">Accuracy Degradation Under Shift</h3>
          <p className="text-xs text-charcoal-500 mt-0.5">
            Drop relative to unperturbed H&E in percentage points ($pp$). Longer downward bars represent worse performance.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs flex-shrink-0">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-[#D47363]" />
            <span className="text-charcoal-600">Baseline Drop</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-[#CC785C]" />
            <span className="text-charcoal-900 font-semibold">Robust Drop</span>
          </div>
        </div>
      </div>

      <div className="w-full overflow-x-auto pb-2">
        <div className="min-w-[560px]">
          <svg viewBox="0 0 580 250" className="w-full h-auto overflow-visible" role="img" aria-label="Accuracy drop in percentage points">
            {/* Zero line at top */}
            <line x1="80" y1="20" x2="560" y2="20" stroke="#7A756D" strokeWidth="1.5" />
            <text x="72" y="24" textAnchor="end" fontSize="10" fill="#3D3A37" className="font-mono">
              0.0 pp
            </text>

            {/* Grid lines */}
            {[20, 40, 60, 80].map((drop) => {
              const y = 20 + (drop / maxDrop) * chartHeight;
              return (
                <g key={drop}>
                  <line x1="80" y1={y} x2="560" y2={y} stroke="#EDE7DE" strokeDasharray="3 3" />
                  <text x="72" y={y + 3} textAnchor="end" fontSize="10" fill="#8C857B" className="font-mono">
                    -{drop} pp
                  </text>
                </g>
              );
            })}

            {/* Bars */}
            {nonOriginal.map((row, idx) => {
              const x = 95 + idx * 66;
              const bHeight = Math.min((Math.abs(row.baseline_drop_pct) / maxDrop) * chartHeight, chartHeight);
              const rHeight = Math.min((Math.abs(row.robust_drop_pct) / maxDrop) * chartHeight, chartHeight);

              return (
                <g key={row.condition}>
                  {/* Baseline drop bar */}
                  <rect x={x} y="20" width="16" height={bHeight} fill="#D47363" rx="3" />
                  <text
                    x={x + 8}
                    y={20 + bHeight + (bHeight < 25 ? 14 : 12)}
                    textAnchor="middle"
                    fontSize="9"
                    fill="#9B2A2A"
                    className="font-mono font-medium"
                  >
                    {row.baseline_drop_pct.toFixed(1)}
                  </text>

                  {/* Robust drop bar */}
                  <rect x={x + 19} y="20" width="16" height={rHeight} fill="#CC785C" rx="3" />
                  <text
                    x={x + 27}
                    y={20 + rHeight + (rHeight < 25 ? 14 : 12)}
                    textAnchor="middle"
                    fontSize="9"
                    fill="#7D3B29"
                    className="font-mono font-bold"
                  >
                    {row.robust_drop_pct.toFixed(1)}
                  </text>

                  {/* Condition label */}
                  <text
                    x={x + 17}
                    y="235"
                    textAnchor="middle"
                    fontSize="9"
                    fill="#3D3A37"
                    className="font-sans font-medium"
                  >
                    {SHORT_NAMES[row.condition] || row.condition.replace(/_/g, " ")}
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
