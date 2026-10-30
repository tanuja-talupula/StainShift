import React from "react";
import { ConditionResult } from "@/lib/types";

interface Props {
  baselineResults: Record<string, ConditionResult>;
  robustResults: Record<string, ConditionResult>;
  conditions: string[];
}

const SHORT_NAMES: Record<string, string> = {
  original: "Original",
  reconstruction_only: "Deconv Only",
  heavy_hematoxylin: "Heavy Hem.",
  heavy_eosin: "Heavy Eosin",
  pale_understained: "Pale Under.",
  dark_overstained: "Dark Over.",
  synthetic_warm_shift: "Warm Shift",
  synthetic_cool_shift: "Cool Shift",
};

export function MacroF1Chart({ baselineResults, robustResults, conditions }: Props) {
  const chartHeight = 180;

  return (
    <div className="bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-sm space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div>
          <h3 className="font-serif text-lg font-medium text-charcoal-900">Macro F1 Score by Condition</h3>
          <p className="text-xs text-charcoal-500 mt-0.5">
            Balanced F1 metric averaged equally across all 9 tissue classes (range 0.0 to 1.0).
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs flex-shrink-0">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-[#A8A196]" />
            <span className="text-charcoal-600">Baseline</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-[#CC785C]" />
            <span className="text-charcoal-900 font-semibold">Stain-Robust</span>
          </div>
        </div>
      </div>

      <div className="w-full overflow-x-auto pb-2">
        <div className="min-w-[560px]">
          <svg viewBox="0 0 580 250" className="w-full h-auto overflow-visible" role="img" aria-label="Macro F1 score comparison">
            {[0, 0.25, 0.5, 0.75, 1.0].map((val) => {
              const y = 20 + (1 - val) * chartHeight;
              return (
                <g key={val}>
                  <line x1="45" y1={y} x2={560} y2={y} stroke="#EDE7DE" strokeDasharray="3 3" />
                  <text x="35" y={y + 3} textAnchor="end" fontSize="10" fill="#8C857B" className="font-mono">
                    {val.toFixed(2)}
                  </text>
                </g>
              );
            })}

            {conditions.map((cond, idx) => {
              const bF1 = baselineResults[cond]?.macro_f1 || 0;
              const rF1 = robustResults[cond]?.macro_f1 || 0;
              const x = 55 + idx * 64;
              const bHeight = bF1 * chartHeight;
              const rHeight = rF1 * chartHeight;
              const bY = 20 + (chartHeight - bHeight);
              const rY = 20 + (chartHeight - rHeight);

              return (
                <g key={cond}>
                  {/* Baseline bar */}
                  <rect x={x} y={bY} width="16" height={bHeight} fill="#A8A196" rx="3" />
                  <text x={x + 8} y={bY - 4} textAnchor="middle" fontSize="8.5" fill="#5A554D" className="font-mono">
                    {bF1.toFixed(2)}
                  </text>

                  {/* Robust bar */}
                  <rect x={x + 18} y={rY} width="16" height={rHeight} fill="#CC785C" rx="3" />
                  <text x={x + 26} y={rY - 4} textAnchor="middle" fontSize="8.5" fill="#7D3B29" className="font-mono font-bold">
                    {rF1.toFixed(2)}
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
                    {SHORT_NAMES[cond] || cond.replace(/_/g, " ")}
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
