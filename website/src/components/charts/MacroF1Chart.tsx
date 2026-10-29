import React from "react";
import { ConditionResult } from "@/lib/types";

interface Props {
  baselineResults: Record<string, ConditionResult>;
  robustResults: Record<string, ConditionResult>;
  conditions: string[];
}

export function MacroF1Chart({ baselineResults, robustResults, conditions }: Props) {
  const chartHeight = 220;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-900">Macro F1 Score by Condition</h3>
        <p className="text-xs text-slate-500">
          Unweighted average of F1 across all 9 colorectal tissue classes (accounting for class imbalance).
        </p>
      </div>

      <div className="w-full overflow-x-auto pb-2">
        <div className="min-w-[560px]">
          <svg viewBox="0 0 580 260" className="w-full h-auto overflow-visible" role="img" aria-label="Macro F1 score comparison">
            {[0, 0.25, 0.5, 0.75, 1.0].map((val) => {
              const y = chartHeight - val * chartHeight + 15;
              return (
                <g key={val}>
                  <line x1="45" y1={y} x2="560" y2={y} stroke="#e2e8f0" strokeDasharray="3 3" />
                  <text x="35" y={y + 3} textAnchor="end" fontSize="10" fill="#64748b" className="font-mono">
                    {val.toFixed(2)}
                  </text>
                </g>
              );
            })}

            {conditions.map((cond, idx) => {
              const bF1 = baselineResults[cond]?.macro_f1 || 0;
              const rF1 = robustResults[cond]?.macro_f1 || 0;
              const x = 55 + idx * 62;
              const bHeight = bF1 * chartHeight;
              const rHeight = rF1 * chartHeight;
              const bY = chartHeight - bHeight + 15;
              const rY = chartHeight - rHeight + 15;

              return (
                <g key={cond}>
                  <rect x={x} y={bY} width="16" height={bHeight} fill="#94a3b8" rx="2" />
                  <text x={x + 8} y={bY - 4} textAnchor="middle" fontSize="8.5" fill="#475569" className="font-mono">
                    {bF1.toFixed(2)}
                  </text>

                  <rect x={x + 18} y={rY} width="16" height={rHeight} fill="#0284c7" rx="2" />
                  <text x={x + 26} y={rY - 4} textAnchor="middle" fontSize="8.5" fill="#0369a1" className="font-mono font-bold">
                    {rF1.toFixed(2)}
                  </text>

                  <text
                    x={x + 17}
                    y={chartHeight + 32}
                    textAnchor="middle"
                    fontSize="9"
                    fill="#334155"
                    className="font-medium"
                  >
                    {cond.replace(/_/g, " ")}
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
