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
    <div className="bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-sm space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="font-serif text-lg font-medium text-charcoal-900">Held-Out Test Confusion Matrix</h3>
          <p className="text-xs text-charcoal-500 mt-0.5">
            Row: Actual Ground Truth Tissue Class | Column: Model Predicted Class (N = 1,077 patches)
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Model toggle */}
          <div className="inline-flex rounded-full border border-[#E8E4DD] p-0.5 bg-[#FAF8F5] text-xs">
            <button
              type="button"
              onClick={() => setSelectedModel("baseline")}
              className={`px-3 py-1 rounded-full font-medium transition ${
                selectedModel === "baseline" ? "bg-white text-charcoal-900 shadow-sm" : "text-charcoal-500 hover:text-charcoal-900"
              }`}
            >
              Baseline
            </button>
            <button
              type="button"
              onClick={() => setSelectedModel("robust_stain_aug")}
              className={`px-3 py-1 rounded-full font-medium transition ${
                selectedModel === "robust_stain_aug" ? "bg-charcoal-900 text-white shadow-sm" : "text-charcoal-500 hover:text-charcoal-900"
              }`}
            >
              Stain-Robust
            </button>
          </div>

          {/* Condition Selector */}
          <select
            value={selectedCondition}
            onChange={(e) => setSelectedCondition(e.target.value)}
            className="text-xs border border-[#E8E4DD] rounded-xl px-3 py-1.5 bg-white text-charcoal-800 font-medium focus:ring-1 focus:ring-[#CC785C]"
            aria-label="Select stain condition for confusion matrix"
          >
            {conditions.map((cond) => (
              <option key={cond} value={cond}>
                {cond.replace(/_/g, " ")} {cond === "reconstruction_only" ? "(Deconv Control)" : ""}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Matrix Display Table */}
      <div className="w-full overflow-x-auto border border-[#E8E4DD] rounded-xl">
        <table className="w-full border-collapse text-center text-xs font-mono">
          <thead>
            <tr className="bg-[#FAF8F5] border-b border-[#E8E4DD] text-charcoal-500">
              <th className="p-2 border-r border-[#E8E4DD] text-left font-sans text-[11px] font-semibold">
                Actual \ Pred
              </th>
              {classNames.map((cls) => (
                <th key={cls} className="p-2 font-bold text-charcoal-700 min-w-[36px]">
                  {cls}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, rowIdx) => {
              const actualClass = classNames[rowIdx];
              return (
                <tr key={actualClass} className="border-b border-[#E8E4DD] last:border-b-0">
                  <td className="p-2 font-bold font-sans text-left bg-[#FAF8F5] border-r border-[#E8E4DD] text-charcoal-800">
                    {actualClass}
                  </td>
                  {row.map((val, colIdx) => {
                    const isDiagonal = rowIdx === colIdx;
                    const intensity = val / maxVal;

                    return (
                      <td
                        key={colIdx}
                        className="p-2 font-medium transition"
                        style={{
                          backgroundColor:
                            val === 0
                              ? "transparent"
                              : isDiagonal
                              ? `rgba(204, 120, 92, ${Math.max(intensity * 0.85, 0.15)})`
                              : `rgba(184, 58, 58, ${Math.max(intensity * 0.7, 0.12)})`,
                          color: val > maxVal * 0.5 ? "#ffffff" : "#1A1918",
                        }}
                        title={`Actual: ${actualClass}, Predicted: ${classNames[colIdx]} (${val} patches)`}
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

      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-charcoal-500 pt-1">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#CC785C]" />
            <span>Correct Classifications (Diagonal)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#D47363]" />
            <span>Misclassifications (Off-Diagonal)</span>
          </div>
        </div>
        <span className="font-mono text-[11px] text-charcoal-400">
          Accuracy: {activeResult ? activeResult.accuracy.toFixed(2) : "0.00"}% | Macro F1: {activeResult?.macro_f1.toFixed(4)}
        </span>
      </div>
    </div>
  );
}
