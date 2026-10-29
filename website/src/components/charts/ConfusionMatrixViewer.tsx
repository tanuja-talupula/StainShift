"use client";

import React, { useState } from "react";
import { ConditionResult } from "@/lib/types";

interface Props {
  baselineResults: Record<string, ConditionResult>;
  robustResults: Record<string, ConditionResult>;
  conditions: string[];
  classNames: string[];
}

export function ConfusionMatrixViewer({
  baselineResults,
  robustResults,
  conditions,
  classNames,
}: Props) {
  const [selectedCondition, setSelectedCondition] = useState<string>("reconstruction_only");
  const [selectedModel, setSelectedModel] = useState<"baseline" | "robust_stain_aug">("robust_stain_aug");

  const activeResult = selectedModel === "baseline" ? baselineResults[selectedCondition] : robustResults[selectedCondition];
  const matrix = activeResult?.confusion_matrix || [];

  // Find max value in matrix for color scaling
  const maxVal = matrix.reduce((max, row) => Math.max(max, ...row), 1);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-slate-900">Held-Out Test Confusion Matrix</h3>
          <p className="text-xs text-slate-500">
            Row: Actual Ground Truth Tissue Class | Column: Model Predicted Class ($N = 1,077$ patches)
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Model toggle */}
          <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50 text-xs">
            <button
              type="button"
              onClick={() => setSelectedModel("baseline")}
              className={`px-2.5 py-1 rounded-md font-medium transition ${
                selectedModel === "baseline" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Baseline
            </button>
            <button
              type="button"
              onClick={() => setSelectedModel("robust_stain_aug")}
              className={`px-2.5 py-1 rounded-md font-medium transition ${
                selectedModel === "robust_stain_aug" ? "bg-brand-600 text-white shadow-sm" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Stain-Robust
            </button>
          </div>

          {/* Condition Selector */}
          <select
            value={selectedCondition}
            onChange={(e) => setSelectedCondition(e.target.value)}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-800 font-medium focus:ring-1 focus:ring-brand-500"
            aria-label="Select stain condition for confusion matrix"
          >
            {conditions.map((cond) => (
              <option key={cond} value={cond}>
                {cond.replace(/_/g, " ")} {cond === "reconstruction_only" ? "(Control)" : ""}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Accuracy & F1 metric summary for selection */}
      <div className="flex items-center gap-4 text-xs bg-slate-50 border border-slate-100 p-3 rounded-lg">
        <span className="text-slate-600">
          Condition: <strong className="text-slate-900">{selectedCondition}</strong>
        </span>
        <span>•</span>
        <span className="text-slate-600">
          Accuracy: <strong className="text-brand-700 font-mono">{activeResult?.accuracy.toFixed(2)}%</strong>
        </span>
        <span>•</span>
        <span className="text-slate-600">
          Macro F1: <strong className="text-brand-700 font-mono">{activeResult?.macro_f1.toFixed(4)}</strong>
        </span>
      </div>

      {/* 9x9 Grid */}
      <div className="overflow-x-auto">
        <div className="min-w-[480px]">
          <table className="w-full text-center border-collapse text-xs">
            <thead>
              <tr>
                <th className="p-1 text-[10px] text-slate-400 font-mono">True \ Pred</th>
                {classNames.map((cl) => (
                  <th key={cl} className="p-1 font-mono font-semibold text-slate-700 text-[11px]">
                    {cl}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.map((row, rIdx) => {
                const trueClass = classNames[rIdx];
                return (
                  <tr key={trueClass}>
                    <th scope="row" className="p-1 text-right font-mono font-semibold text-slate-700 text-[11px] pr-2">
                      {trueClass}
                    </th>
                    {row.map((val, cIdx) => {
                      const isDiagonal = rIdx === cIdx;
                      const intensity = val > 0 ? Math.min(val / maxVal, 1) : 0;
                      // Color styling
                      let bgStyle = "rgba(241, 245, 249, 0.4)";
                      let textStyle = "text-slate-400";
                      if (val > 0) {
                        if (isDiagonal) {
                          bgStyle = `rgba(2, 132, 199, ${Math.max(intensity, 0.15)})`;
                          textStyle = intensity > 0.5 ? "text-white font-bold" : "text-brand-900 font-semibold";
                        } else {
                          bgStyle = `rgba(239, 68, 68, ${Math.max(intensity, 0.15)})`;
                          textStyle = intensity > 0.5 ? "text-white font-bold" : "text-red-900 font-semibold";
                        }
                      }
                      return (
                        <td
                          key={cIdx}
                          style={{ backgroundColor: bgStyle }}
                          className={`p-1.5 border border-white text-[11px] font-mono transition ${textStyle}`}
                          title={`True: ${trueClass}, Predicted: ${classNames[cIdx]} (${val} samples)`}
                        >
                          {val}
                        </td>
                      );
                    })}
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
