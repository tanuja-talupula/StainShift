"use client";

import React, { useState } from "react";
import { DemoManifest, DemoExample } from "@/lib/types";
import { CheckCircle2, XCircle, ShieldCheck } from "lucide-react";

interface Props {
  manifest: DemoManifest;
}

export function DemoExplorer({ manifest }: Props) {
  const [selectedClassIdx, setSelectedClassIdx] = useState<number>(8); // Default to TUM (Tumor)
  const [selectedCondition, setSelectedCondition] = useState<string>("reconstruction_only");

  const example: DemoExample = manifest.examples[selectedClassIdx];
  const conditionData = example?.conditions[selectedCondition];
  const origConditionData = example?.conditions["original"];

  return (
    <div className="space-y-8">
      {/* Selection Rules & Manifest Attribution Card */}
      <div className="p-4 rounded-2xl bg-[#FAF8F5] border border-[#E8E4DD] shadow-xs space-y-1.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 text-charcoal-700">
            <ShieldCheck className="w-4 h-4 text-[#2D5A46] flex-shrink-0" />
            <span>
              <strong>Selection Criterion:</strong> {manifest.metadata.selection_rule}
            </span>
          </div>
          <span className="font-mono text-charcoal-400 text-[11px]">
            Split Manifest SHA-256: {manifest.metadata.frozen_split_manifest_sha256.slice(0, 12)}...
          </span>
        </div>
        <p className="text-xs text-charcoal-500 leading-relaxed">
          Deterministic held-out test patches evaluated across all 8 synthetic stain profiles with zero backend connection required.
        </p>
      </div>

      {/* Tissue Class Selector Tabs */}
      <div className="space-y-2.5">
        <label className="text-xs font-semibold uppercase tracking-wider text-charcoal-600 block">
          Select Colorectal Tissue Class (9 Classes Available):
        </label>
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Colorectal tissue classes">
          {manifest.examples.map((ex, idx) => {
            const isSelected = idx === selectedClassIdx;
            return (
              <button
                key={ex.tissue_class}
                type="button"
                role="tab"
                aria-selected={isSelected}
                onClick={() => setSelectedClassIdx(idx)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-charcoal-900 text-white font-semibold shadow-sm"
                    : "bg-white text-charcoal-700 border border-[#E8E4DD] hover:bg-[#FAF8F5] hover:border-[#D5CEC2]"
                }`}
              >
                <span className="font-mono font-bold">{ex.tissue_class}</span>
                <span className="text-[11px] opacity-75">({ex.tissue_class_description})</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Stain Condition Selector */}
      <div className="space-y-2.5">
        <label className="text-xs font-semibold uppercase tracking-wider text-charcoal-600 block">
          Select Stain Condition:
        </label>
        <div className="flex flex-wrap gap-2">
          {manifest.conditions.map((cond) => {
            const isSelected = cond === selectedCondition;
            const isControl = cond === "reconstruction_only";
            return (
              <button
                key={cond}
                type="button"
                onClick={() => setSelectedCondition(cond)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition ${
                  isSelected
                    ? "bg-[#EDE7DE] text-charcoal-900 font-semibold border border-[#DDD7CC] shadow-xs"
                    : "bg-white text-charcoal-600 border border-[#E8E4DD] hover:bg-[#FAF8F5]"
                }`}
              >
                {cond.replace(/_/g, " ")} {isControl ? "(Deconv Control)" : ""}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Inspection Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Images Column */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-sm space-y-5">
          <div className="flex items-center justify-between border-b border-[#E8E4DD] pb-3">
            <h4 className="text-xs font-mono font-bold text-charcoal-900">Patch: {example.patch_id}</h4>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#EDE7DE] font-mono text-charcoal-800 font-medium">
              True: {example.tissue_class}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Original reference patch */}
            <div className="space-y-1.5 text-center">
              <span className="text-xs font-medium text-charcoal-700 block">Original (Unperturbed)</span>
              <div className="relative aspect-square w-full rounded-xl overflow-hidden border border-[#E8E4DD] bg-[#FAF8F5]">
                <img
                  src={origConditionData?.image_url}
                  alt={`Original patch for ${example.tissue_class}`}
                  className="w-full h-full object-cover"
                />
              </div>
              <span className="text-[10px] text-charcoal-400 font-mono">224×224 RGB PNG</span>
            </div>

            {/* Shifted patch */}
            <div className="space-y-1.5 text-center">
              <span className="text-xs font-medium text-charcoal-900 block truncate">
                {selectedCondition.replace(/_/g, " ")}
              </span>
              <div className="relative aspect-square w-full rounded-xl overflow-hidden border border-[#CC785C] bg-[#FAF8F5] shadow-xs">
                <img
                  src={conditionData?.image_url}
                  alt={`${selectedCondition} patch for ${example.tissue_class}`}
                  className="w-full h-full object-cover"
                />
              </div>
              <span className="text-[10px] text-[#CC785C] font-semibold">Applied Transform</span>
            </div>
          </div>

          <div className="p-3.5 bg-[#FAF8F5] border border-[#E8E4DD] rounded-xl text-xs text-charcoal-600 space-y-1">
            <p>
              <strong>Tissue Type:</strong> {example.tissue_class_description}
            </p>
            <p className="font-mono text-[11px] text-charcoal-400">
              Source file: {example.source_relative_path}
            </p>
          </div>
        </div>

        {/* Predictions & Model Comparison Column */}
        <div className="lg:col-span-7 space-y-5">
          {/* Baseline Model Result Card */}
          <div className={`p-6 rounded-2xl border transition shadow-sm bg-white ${
            conditionData?.baseline.is_correct ? "border-[#E8E4DD]" : "border-[#F2D6D6] bg-[#FAF5F5]"
          }`}>
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#E8E4DD]/60">
              <div>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-charcoal-400">Standard Model</span>
                <h4 className="font-serif text-base font-medium text-charcoal-900">Baseline MobileNetV3</h4>
              </div>
              <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
                conditionData?.baseline.is_correct ? "bg-[#EDF4EF] text-[#244737] border border-[#D5E5DA]" : "bg-[#FBEFEF] text-[#9B2A2A] border border-[#F2D6D6]"
              }`}>
                {conditionData?.baseline.is_correct ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#2D5A46]" />
                    <span>Correct ({conditionData.baseline.predicted_class})</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-3.5 h-3.5 text-[#B83A3A]" />
                    <span>Misclassified as {conditionData?.baseline.predicted_class}</span>
                  </>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-xs text-charcoal-600">
                <span>Confidence in Prediction:</span>
                <span className="font-mono font-bold text-charcoal-900">{(conditionData?.baseline.confidence! * 100).toFixed(2)}%</span>
              </div>
              {/* Top probabilities bars */}
              <div className="space-y-1.5 pt-1">
                {Object.entries(conditionData?.baseline.probabilities || {})
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 3)
                  .map(([cls, prob]) => (
                    <div key={cls} className="text-xs flex items-center gap-3">
                      <span className="font-mono w-12 text-charcoal-700">{cls}:</span>
                      <div className="flex-1 h-2 rounded-full bg-[#FAF8F5] overflow-hidden border border-[#E8E4DD]">
                        <div
                          className={`h-full rounded-full ${cls === example.tissue_class ? "bg-[#2D5A46]" : "bg-[#A8A196]"}`}
                          style={{ width: `${prob * 100}%` }}
                        />
                      </div>
                      <span className="font-mono w-14 text-right text-charcoal-500">{(prob * 100).toFixed(1)}%</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          {/* Stain-Robust Model Result Card */}
          <div className="p-6 rounded-2xl border border-[#E8E4DD] bg-white shadow-sm">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#E8E4DD]/60">
              <div>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-[#CC785C]">Physics-Augmented</span>
                <h4 className="font-serif text-base font-medium text-charcoal-900">Stain-Robust MobileNetV3 (Beer-Lambert)</h4>
              </div>
              <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
                conditionData?.robust_stain_aug.is_correct ? "bg-[#EDF4EF] text-[#244737] border border-[#D5E5DA]" : "bg-[#FBEFEF] text-[#9B2A2A] border border-[#F2D6D6]"
              }`}>
                {conditionData?.robust_stain_aug.is_correct ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#2D5A46]" />
                    <span>Correct ({conditionData.robust_stain_aug.predicted_class})</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-3.5 h-3.5 text-[#B83A3A]" />
                    <span>Misclassified as {conditionData?.robust_stain_aug.predicted_class}</span>
                  </>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-xs text-charcoal-600">
                <span>Confidence in Prediction:</span>
                <span className="font-mono font-bold text-[#CC785C]">
                  {(conditionData?.robust_stain_aug.confidence! * 100).toFixed(2)}%
                </span>
              </div>
              {/* Top probabilities bars */}
              <div className="space-y-1.5 pt-1">
                {Object.entries(conditionData?.robust_stain_aug.probabilities || {})
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 3)
                  .map(([cls, prob]) => (
                    <div key={cls} className="text-xs flex items-center gap-3">
                      <span className="font-mono w-12 text-charcoal-700">{cls}:</span>
                      <div className="flex-1 h-2 rounded-full bg-[#FAF8F5] overflow-hidden border border-[#E8E4DD]">
                        <div
                          className={`h-full rounded-full ${cls === example.tissue_class ? "bg-[#2D5A46]" : "bg-[#CC785C]"}`}
                          style={{ width: `${prob * 100}%` }}
                        />
                      </div>
                      <span className="font-mono w-14 text-right text-charcoal-500">{(prob * 100).toFixed(1)}%</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
