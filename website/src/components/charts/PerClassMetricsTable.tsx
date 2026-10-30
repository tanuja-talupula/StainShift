"use client";

import React, { useState } from "react";
import { ConditionResult } from "@/lib/types";

interface Props {
  baselineResults: Record<string, ConditionResult>;
  robustResults: Record<string, ConditionResult>;
  conditions: string[];
  classNames: string[];
  classDescriptions?: Record<string, string>;
}

const CLASS_DESCRIPTIONS: Record<string, string> = {
  ADI: "Adipose tissue (fat cells)",
  BACK: "Background / glass / slide artifact",
  DEB: "Necrotic tissue & cellular debris",
  LYM: "Lymphocytes (immune infiltration)",
  MUC: "Mucus (mucin pools)",
  MUS: "Smooth muscle layer",
  NORM: "Normal colorectal mucosa",
  STR: "Cancer-associated stroma (fibroblasts/collagen)",
  TUM: "Colorectal adenocarcinoma epithelium (tumor)",
};

const CONDITION_LABELS: Record<string, string> = {
  original: "Original (Unperturbed H&E)",
  reconstruction_only: "Deconvolution Reconstruction Control",
  heavy_hematoxylin: "Heavy Hematoxylin (Hyperchromatic Nuclei)",
  heavy_eosin: "Heavy Eosin (Eosinophilic Cytoplasm)",
  pale_understained: "Pale / Understained (Dilute Dye)",
  dark_overstained: "Dark / Overstained (Concentrated Dye)",
  synthetic_warm_shift: "Synthetic Warm Shift (Acidic Red/Yellow)",
  synthetic_cool_shift: "Synthetic Cool Shift (Basic Blue/Purple)",
};

export function PerClassMetricsTable({
  baselineResults,
  robustResults,
  conditions,
  classNames,
  classDescriptions = CLASS_DESCRIPTIONS,
}: Props) {
  const [selectedCondition, setSelectedCondition] = useState<string>("reconstruction_only");

  const baseResult = baselineResults[selectedCondition];
  const robResult = robustResults[selectedCondition];

  return (
    <div className="bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-sm space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="font-serif text-lg font-medium text-charcoal-900">Per-Class Diagnostic Performance</h3>
          <p className="text-xs text-charcoal-500 mt-0.5">
            Breakdown across all 9 colorectal tissue classes on held-out test cohort ($N = 1,077$ patches).
          </p>
        </div>

        {/* Condition Selector */}
        <div className="flex items-center gap-2">
          <label htmlFor="per-class-condition-select" className="text-xs text-charcoal-500 font-medium">
            Stain Condition:
          </label>
          <select
            id="per-class-condition-select"
            value={selectedCondition}
            onChange={(e) => setSelectedCondition(e.target.value)}
            className="text-xs border border-[#E8E4DD] rounded-xl px-3 py-1.5 bg-[#FAF8F5] text-charcoal-800 font-medium focus:ring-1 focus:ring-[#CC785C]"
          >
            {conditions.map((cond) => (
              <option key={cond} value={cond}>
                {CONDITION_LABELS[cond] || cond.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Summary highlight banner */}
      <div className="p-3.5 rounded-xl bg-[#FAF8F5] border border-[#E8E4DD] flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-charcoal-700">
          <span className="font-semibold text-charcoal-900">Active Condition:</span>
          <span>{CONDITION_LABELS[selectedCondition] || selectedCondition}</span>
        </div>
        <div className="flex items-center gap-4 font-mono text-[11px]">
          <span>
            Baseline Acc: <strong className="text-charcoal-800">{baseResult?.accuracy.toFixed(2)}%</strong> (F1: {baseResult?.macro_f1.toFixed(3)})
          </span>
          <span className="text-[#CC785C]">→</span>
          <span>
            Robust Acc: <strong className="text-[#CC785C] font-bold">{robResult?.accuracy.toFixed(2)}%</strong> (F1: {robResult?.macro_f1.toFixed(3)})
          </span>
        </div>
      </div>

      {/* Per-Class Table */}
      <div className="overflow-x-auto border border-[#E8E4DD] rounded-xl">
        <table className="w-full text-left text-xs text-charcoal-700">
          <thead className="bg-[#FAF8F5] border-b border-[#E8E4DD] text-charcoal-500 font-medium">
            <tr>
              <th scope="col" className="py-2.5 px-3">Class</th>
              <th scope="col" className="py-2.5 px-3">Biological Tissue Type</th>
              <th scope="col" className="py-2.5 px-3 text-right">Support ($N$)</th>
              <th scope="col" className="py-2.5 px-3 text-right">Base Prec.</th>
              <th scope="col" className="py-2.5 px-3 text-right">Base Recall</th>
              <th scope="col" className="py-2.5 px-3 text-right">Base F1</th>
              <th scope="col" className="py-2.5 px-3 text-right">Robust Prec.</th>
              <th scope="col" className="py-2.5 px-3 text-right">Robust Recall</th>
              <th scope="col" className="py-2.5 px-3 text-right font-bold text-charcoal-900">Robust F1</th>
              <th scope="col" className="py-2.5 px-3 text-right font-bold text-[#2D5A46]">F1 Delta</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E8E4DD] font-mono text-[11px]">
            {classNames.map((cls) => {
              const bClass = baseResult?.per_class?.[cls];
              const rClass = robResult?.per_class?.[cls];
              const support = bClass?.support || rClass?.support || 0;
              const f1Delta = (rClass?.f1 ?? 0) - (bClass?.f1 ?? 0);

              const isSevereCollapse = (bClass?.f1 ?? 0) < 0.5 && (rClass?.f1 ?? 0) >= 0.85;

              return (
                <tr
                  key={cls}
                  className={`hover:bg-[#FAF8F5] transition ${
                    isSevereCollapse ? "bg-[#FAF5F2]" : ""
                  }`}
                >
                  <td className="py-2.5 px-3 font-sans font-bold text-charcoal-900">
                    <span className="inline-block px-1.5 py-0.5 rounded bg-[#EDE7DE] text-[10px]">
                      {cls}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-sans text-charcoal-700">
                    {classDescriptions[cls] || cls}
                    {cls === "TUM" && (
                      <span className="ml-1.5 inline-block text-[9.5px] uppercase font-semibold text-[#CC785C] bg-[#F7EBE8] px-1.5 py-0.2 rounded">
                        Critical Target
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-right text-charcoal-500 font-sans">{support}</td>
                  <td className="py-2.5 px-3 text-right text-charcoal-600">
                    {bClass ? bClass.precision.toFixed(3) : "—"}
                  </td>
                  <td className="py-2.5 px-3 text-right text-charcoal-600">
                    {bClass ? bClass.recall.toFixed(3) : "—"}
                  </td>
                  <td className={`py-2.5 px-3 text-right font-medium ${
                    (bClass?.f1 ?? 0) < 0.5 ? "text-[#9B2A2A] font-bold" : "text-charcoal-700"
                  }`}>
                    {bClass ? bClass.f1.toFixed(3) : "—"}
                  </td>
                  <td className="py-2.5 px-3 text-right text-charcoal-800">
                    {rClass ? rClass.precision.toFixed(3) : "—"}
                  </td>
                  <td className="py-2.5 px-3 text-right text-charcoal-800">
                    {rClass ? rClass.recall.toFixed(3) : "—"}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-[#CC785C]">
                    {rClass ? rClass.f1.toFixed(3) : "—"}
                  </td>
                  <td className={`py-2.5 px-3 text-right font-bold ${
                    f1Delta > 0.1 ? "text-[#2D5A46]" : f1Delta < -0.05 ? "text-[#9B2A2A]" : "text-charcoal-500"
                  }`}>
                    {f1Delta > 0 ? `+${f1Delta.toFixed(3)}` : f1Delta.toFixed(3)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-[11px] text-charcoal-500 italic">
        Note: Under stain deconvolution without dye variation, baseline model tumor (TUM) recall collapses to{" "}
        <strong className="font-semibold text-[#9B2A2A]">0.12</strong> due to ERM color-texture shortcut reliance.
        StainShift robust training restores tumor recall to <strong className="font-semibold text-[#2D5A46]">0.99</strong>.
      </p>
    </div>
  );
}
