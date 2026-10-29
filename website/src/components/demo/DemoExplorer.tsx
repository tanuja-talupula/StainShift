"use client";

import React, { useState } from "react";
import Image from "next/image";
import { DemoManifest, DemoExample } from "@/lib/types";
import { CheckCircle2, XCircle, ShieldCheck, Info } from "lucide-react";

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
      <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 text-slate-700">
            <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>
              <strong>Selection Criterion:</strong> {manifest.metadata.selection_rule}
            </span>
          </div>
          <span className="font-mono text-slate-500 text-[11px]">
            Split Manifest SHA-256: {manifest.metadata.frozen_split_manifest_sha256.slice(0, 12)}...
          </span>
        </div>
        <p className="text-xs text-slate-500 leading-relaxed">
          {manifest.metadata.disclaimer} Each probability distribution is generated directly from the Stage A PyTorch weights.
        </p>
      </div>

      {/* Tissue Class Selector Tabs */}
      <div className="space-y-2">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
          Select Colorectal Tissue Class (9 Classes Available):
        </label>
        <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Colorectal tissue classes">
          {manifest.examples.map((ex, idx) => {
            const isSelected = idx === selectedClassIdx;
            return (
              <button
                key={ex.tissue_class}
                type="button"
                role="tab"
                aria-selected={isSelected}
                onClick={() => setSelectedClassIdx(idx)}
                className={`px-3 py-2 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-brand-600 text-white shadow-sm font-semibold"
                    : "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50"
                }`}
              >
                <span className="font-mono">{ex.tissue_class}</span>
                <span className="text-[11px] opacity-80">({ex.tissue_class_description})</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Stain Condition Selector */}
      <div className="space-y-2">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
          Select Stain Condition:
        </label>
        <div className="flex flex-wrap gap-1.5">
          {manifest.conditions.map((cond) => {
            const isSelected = cond === selectedCondition;
            const isControl = cond === "reconstruction_only";
            return (
              <button
                key={cond}
                type="button"
                onClick={() => setSelectedCondition(cond)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                  isSelected
                    ? "bg-slate-900 text-white font-semibold shadow-sm"
                    : "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50"
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
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-slate-900 font-mono">Patch: {example.patch_id}</h4>
            <span className="text-xs px-2 py-0.5 rounded bg-slate-100 font-mono text-slate-700">
              True: {example.tissue_class}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Original reference patch */}
            <div className="space-y-1.5 text-center">
              <span className="text-xs font-semibold text-slate-700">Original (Unperturbed)</span>
              <div className="relative aspect-square w-full rounded-lg overflow-hidden border border-slate-200 bg-slate-100">
                <img
                  src={origConditionData?.image_url}
                  alt={`Original patch for ${example.tissue_class}`}
                  className="w-full h-full object-cover"
                />
              </div>
              <span className="text-[10px] text-slate-400 font-mono">224x224 RGB PNG</span>
            </div>

            {/* Shifted patch */}
            <div className="space-y-1.5 text-center">
              <span className="text-xs font-semibold text-slate-900 flex items-center justify-center gap-1">
                <span>{selectedCondition.replace(/_/g, " ")}</span>
              </span>
              <div className="relative aspect-square w-full rounded-lg overflow-hidden border-2 border-brand-500 bg-slate-100 shadow-sm">
                <img
                  src={conditionData?.image_url}
                  alt={`${selectedCondition} patch for ${example.tissue_class}`}
                  className="w-full h-full object-cover"
                />
              </div>
              <span className="text-[10px] text-brand-600 font-medium">Applied Transformation</span>
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-100 rounded-lg text-xs text-slate-600 space-y-1">
            <p>
              <strong>Tissue Type:</strong> {example.tissue_class_description}
            </p>
            <p className="font-mono text-[11px] text-slate-400">
              Source file: {example.source_relative_path}
            </p>
          </div>
        </div>

        {/* Predictions & Model Comparison Column */}
        <div className="lg:col-span-7 space-y-5">
          {/* Baseline Model Result Card */}
          <div className={`p-5 rounded-xl border transition shadow-sm bg-white ${
            conditionData?.baseline.is_correct ? "border-slate-200" : "border-red-300 bg-red-50/20"
          }`}>
            <div className="flex items-center justify-between mb-3">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Standard Model</span>
                <h4 className="text-sm font-bold text-slate-900">Baseline MobileNetV3</h4>
              </div>
              <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                conditionData?.baseline.is_correct ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
              }`}>
                {conditionData?.baseline.is_correct ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Correct ({conditionData.baseline.predicted_class})</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-3.5 h-3.5 text-red-600" />
                    <span>Misclassified as {conditionData?.baseline.predicted_class}</span>
                  </>
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between text-xs text-slate-600 mb-1">
                <span>Confidence in Prediction:</span>
                <span className="font-mono font-bold">{(conditionData?.baseline.confidence! * 100).toFixed(2)}%</span>
              </div>
              {/* Top probabilities bars */}
              <div className="space-y-1 pt-1">
                {Object.entries(conditionData?.baseline.probabilities || {})
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 3)
                  .map(([cls, prob]) => (
                    <div key={cls} className="text-xs flex items-center gap-2">
                      <span className="font-mono w-12 text-slate-700">{cls}:</span>
                      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${cls === example.tissue_class ? "bg-emerald-500" : "bg-slate-400"}`}
                          style={{ width: `${prob * 100}%` }}
                        />
                      </div>
                      <span className="font-mono w-14 text-right text-slate-500">{(prob * 100).toFixed(1)}%</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          {/* Stain-Robust Model Result Card */}
          <div className="p-5 rounded-xl border border-brand-200 bg-brand-50/20 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-brand-600">Augmented Model</span>
                <h4 className="text-sm font-bold text-slate-900">Stain-Robust MobileNetV3 (Beer-Lambert)</h4>
              </div>
              <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                conditionData?.robust_stain_aug.is_correct ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
              }`}>
                {conditionData?.robust_stain_aug.is_correct ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Correct ({conditionData.robust_stain_aug.predicted_class})</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-3.5 h-3.5 text-red-600" />
                    <span>Misclassified as {conditionData?.robust_stain_aug.predicted_class}</span>
                  </>
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between text-xs text-slate-600 mb-1">
                <span>Confidence in Prediction:</span>
                <span className="font-mono font-bold text-brand-700">
                  {(conditionData?.robust_stain_aug.confidence! * 100).toFixed(2)}%
                </span>
              </div>
              {/* Top probabilities bars */}
              <div className="space-y-1 pt-1">
                {Object.entries(conditionData?.robust_stain_aug.probabilities || {})
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 3)
                  .map(([cls, prob]) => (
                    <div key={cls} className="text-xs flex items-center gap-2">
                      <span className="font-mono w-12 text-slate-700">{cls}:</span>
                      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${cls === example.tissue_class ? "bg-emerald-500" : "bg-brand-500"}`}
                          style={{ width: `${prob * 100}%` }}
                        />
                      </div>
                      <span className="font-mono w-14 text-right text-slate-500">{(prob * 100).toFixed(1)}%</span>
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
