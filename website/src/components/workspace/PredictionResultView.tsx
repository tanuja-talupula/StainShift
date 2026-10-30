"use client";

import React, { useState } from "react";
import { ImageInferenceResult, SingleModelPrediction } from "@/lib/types";
import { CheckCircle2, AlertTriangle, Layers, ShieldCheck, Cpu } from "lucide-react";

interface Props {
  result: ImageInferenceResult | null;
  activeModelId?: string; // "baseline", "robust_stain_aug", or "compare"
}

export function PredictionResultView({ result, activeModelId = "robust_stain_aug" }: Props) {
  const [viewMode, setViewMode] = useState<"transformed" | "original" | "side_by_side">("side_by_side");

  if (!result) {
    return (
      <div className="h-full min-h-[460px] flex flex-col items-center justify-center p-8 bg-[#FAF8F5] rounded-2xl border border-dashed border-[#DDD7CC] text-center">
        <div className="w-12 h-12 rounded-full bg-white border border-[#E8E4DD] flex items-center justify-center text-charcoal-400 mb-3 shadow-sm">
          <Layers className="w-5 h-5 text-charcoal-500" />
        </div>
        <h3 className="font-serif text-lg font-medium text-charcoal-800">No Image Selected</h3>
        <p className="text-xs text-charcoal-500 max-w-sm mt-1 leading-relaxed">
          Upload histology patches, choose a stain shift condition, and run prediction to inspect real model outputs.
        </p>
      </div>
    );
  }

  if (result.status === "error") {
    return (
      <div className="p-6 bg-[#FBEFEF] rounded-2xl border border-[#F2D6D6] space-y-3">
        <div className="flex items-center gap-2 text-[#9B2A2A] font-semibold text-sm">
          <AlertTriangle className="w-4 h-4 text-[#9B2A2A]" />
          <span>Inference Error: {result.filename}</span>
        </div>
        <p className="text-xs text-[#9B2A2A] font-mono bg-white p-3 rounded-xl border border-[#F2D6D6]">
          {result.error_message || "An unexpected error occurred during processing."}
        </p>
      </div>
    );
  }

  // Determine which model prediction to focus on
  const hasBoth = Boolean(result.predictions.baseline && result.predictions.robust_stain_aug);
  const primaryModelKey = activeModelId === "baseline" ? "baseline" : "robust_stain_aug";
  const primaryPred: SingleModelPrediction = result.predictions[primaryModelKey] || Object.values(result.predictions)[0];

  return (
    <div className="bg-white rounded-2xl border border-[#E8E4DD] shadow-sm p-6 space-y-6">
      {/* Result Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E8E4DD] pb-4">
        <div>
          <span className="font-mono text-xs font-semibold text-[#CC785C] uppercase tracking-wider block">
            {result.filename}
          </span>
          <div className="flex items-center gap-2 text-[11px] text-charcoal-400 mt-0.5">
            {result.original_dimensions && (
              <span>{result.original_dimensions[0]}×{result.original_dimensions[1]} px</span>
            )}
            <span>•</span>
            <span className="capitalize">{result.condition_applied} ({result.intensity_applied.toFixed(2)}x)</span>
            {primaryPred?.inference_time_ms && (
              <>
                <span>•</span>
                <span className="font-mono">{primaryPred.inference_time_ms.toFixed(2)} ms latency</span>
              </>
            )}
          </div>
        </div>

        {/* View Toggle Tabs */}
        <div className="inline-flex rounded-full border border-[#E8E4DD] p-0.5 bg-[#FAF8F5] text-xs">
          <button
            type="button"
            onClick={() => setViewMode("original")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition ${
              viewMode === "original" ? "bg-white text-charcoal-900 shadow-sm" : "text-charcoal-500 hover:text-charcoal-900"
            }`}
          >
            Original
          </button>
          <button
            type="button"
            onClick={() => setViewMode("transformed")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition ${
              viewMode === "transformed" ? "bg-white text-charcoal-900 shadow-sm" : "text-charcoal-500 hover:text-charcoal-900"
            }`}
          >
            Shifted
          </button>
          <button
            type="button"
            onClick={() => setViewMode("side_by_side")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition ${
              viewMode === "side_by_side" ? "bg-white text-charcoal-900 shadow-sm" : "text-charcoal-500 hover:text-charcoal-900"
            }`}
          >
            Side-by-Side
          </button>
        </div>
      </div>

      {/* Visual Image Comparison Container */}
      <div className="bg-[#FAF8F5] p-4 rounded-2xl border border-[#E8E4DD]">
        {viewMode === "side_by_side" ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <span className="text-[11px] font-medium text-charcoal-500 block">
                Original Input Patch
              </span>
              <div className="relative aspect-square w-full rounded-xl overflow-hidden border border-[#E8E4DD] bg-white shadow-xs">
                {result.original_thumbnail_b64 ? (
                  <img
                    src={result.original_thumbnail_b64}
                    alt="Original Patch"
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-xs text-charcoal-400">
                    No preview
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-[11px] font-medium text-charcoal-500 flex items-center justify-between">
                <span>Shifted Image ({result.condition_applied})</span>
              </span>
              <div className="relative aspect-square w-full rounded-xl overflow-hidden border border-[#E8E4DD] bg-white shadow-xs">
                {result.transformed_thumbnail_b64 ? (
                  <img
                    src={result.transformed_thumbnail_b64}
                    alt="Transformed Patch"
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-xs text-charcoal-400">
                    No preview
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <span className="text-xs font-medium text-charcoal-600 mb-2">
              {viewMode === "original" ? "Original Input Patch" : `Shifted Image (${result.condition_applied})`}
            </span>
            <div className="relative w-64 h-64 rounded-xl overflow-hidden border border-[#E8E4DD] bg-white shadow-xs">
              <img
                src={viewMode === "original" ? result.original_thumbnail_b64 || "" : result.transformed_thumbnail_b64 || ""}
                alt="Selected Patch"
                className="w-full h-full object-contain"
              />
            </div>
          </div>
        )}
      </div>

      {/* Comparison Agreement Banner (If comparison mode was selected) */}
      {hasBoth && result.predictions.baseline && result.predictions.robust_stain_aug && (
        <div
          className={`p-4 rounded-2xl border text-xs flex items-start gap-3 ${
            result.agreement
              ? "bg-[#EDF4EF] border-[#D5E5DA] text-[#244737]"
              : "bg-[#FAF4ED] border-[#EDE2D4] text-[#7A4E29]"
          }`}
        >
          {result.agreement ? (
            <CheckCircle2 className="w-4 h-4 text-[#2D5A46] mt-0.5 flex-shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-[#CC785C] mt-0.5 flex-shrink-0" />
          )}
          <div className="space-y-1">
            <div className="font-semibold text-sm">
              {result.agreement ? "Both Models Agree" : "Stain-Induced Prediction Flip Detected"}
            </div>
            <p className="leading-relaxed opacity-90">
              {result.agreement
                ? `Both baseline and robust models agree on classification as ${result.predictions.robust_stain_aug.predicted_class}.`
                : `Baseline predicted ${result.predictions.baseline.predicted_class} while robust model predicted ${result.predictions.robust_stain_aug.predicted_class}.`}
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-1 font-mono text-[11px]">
              <span className="px-2 py-0.5 rounded-full bg-white/70 border border-current">
                Baseline: {result.predictions.baseline.predicted_class} ({(result.predictions.baseline.confidence * 100).toFixed(1)}%)
              </span>
              <span>vs</span>
              <span className="px-2 py-0.5 rounded-full bg-white/70 border border-current font-bold">
                Robust: {result.predictions.robust_stain_aug.predicted_class} ({(result.predictions.robust_stain_aug.confidence * 100).toFixed(1)}%)
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Single Prediction Display (Or Primary Focus) */}
      {primaryPred && (
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-[#E8E4DD] pb-2">
            <div className="flex items-center gap-2">
              <span className="font-serif font-medium text-base text-charcoal-900">
                {primaryModelKey === "baseline" ? "Baseline Model Prediction" : "Stain-Robust Model Prediction"}
              </span>
            </div>
            <span className="text-[11px] text-charcoal-400 font-mono">9-Class Softmax</span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl bg-[#FAF8F5] border border-[#E8E4DD]">
            <div>
              <span className="text-[10px] uppercase font-bold tracking-wider text-charcoal-400 block">
                Top Predicted Class
              </span>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="text-2xl font-serif font-bold text-charcoal-900">
                  {primaryPred.predicted_class}
                </span>
                <span className="text-xs font-medium text-charcoal-600">
                  {primaryPred.predicted_class_description}
                </span>
              </div>
            </div>

            <div className="text-right">
              <span className="text-[10px] uppercase font-bold tracking-wider text-charcoal-400 block">
                Model Confidence
              </span>
              <span className="text-2xl font-serif font-bold font-mono text-charcoal-900">
                {(primaryPred.confidence * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* 9-Class Probability Distribution Bar Chart */}
          <div className="space-y-2 pt-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-charcoal-700 block">
              Class Probabilities:
            </span>
            <div className="space-y-1.5">
              {Object.entries(primaryPred.probabilities)
                .sort(([, a], [, b]) => b - a)
                .map(([cls, prob]) => {
                  const pct = (prob * 100).toFixed(1);
                  const isTop = cls === primaryPred.predicted_class;
                  return (
                    <div key={cls} className="flex items-center gap-3 text-xs">
                      <span className={`w-12 font-mono text-right flex-shrink-0 ${isTop ? "font-bold text-charcoal-900" : "text-charcoal-400"}`}>
                        {cls}
                      </span>
                      <div className="flex-1 h-2 bg-[#FAF8F5] rounded-full overflow-hidden border border-[#E8E4DD]">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${
                            isTop ? "bg-[#CC785C]" : "bg-[#DDD8CF]"
                          }`}
                          style={{ width: `${Math.max(prob * 100, 0.5)}%` }}
                        />
                      </div>
                      <span className={`w-12 font-mono text-[11px] text-right flex-shrink-0 ${isTop ? "font-bold text-charcoal-900" : "text-charcoal-400"}`}>
                        {pct}%
                      </span>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      )}

      {/* Safety Notice */}
      <p className="text-[10px] text-charcoal-400 leading-relaxed italic border-t border-[#E8E4DD] pt-3">
        Research prototype classification only. Softmax confidence does not imply clinical diagnostic certainty.
      </p>
    </div>
  );
}
