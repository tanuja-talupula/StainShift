"use client";

import React, { useState } from "react";
import { ImageInferenceResult, SingleModelPrediction } from "@/lib/types";
import { CheckCircle2, AlertTriangle, Clock, Layers, ShieldCheck, Cpu, ArrowRight } from "lucide-react";

interface Props {
  result: ImageInferenceResult | null;
  activeModelId?: string; // "baseline", "robust_stain_aug", or "compare"
}

const CLASS_COLORS: Record<string, string> = {
  ADI: "bg-amber-400",
  BACK: "bg-slate-300",
  DEB: "bg-stone-500",
  LYM: "bg-indigo-500",
  MUC: "bg-sky-400",
  MUS: "bg-rose-400",
  NORM: "bg-emerald-500",
  STR: "bg-orange-400",
  TUM: "bg-red-600",
};

export function PredictionResultView({ result, activeModelId = "robust_stain_aug" }: Props) {
  const [viewMode, setViewMode] = useState<"transformed" | "original" | "side_by_side">("side_by_side");

  if (!result) {
    return (
      <div className="h-full min-h-[400px] flex flex-col items-center justify-center p-8 bg-slate-50/50 rounded-2xl border border-dashed border-slate-200 text-center">
        <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-3">
          <Layers className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-bold text-slate-800">No Image Selected</h3>
        <p className="text-xs text-slate-500 max-w-sm mt-1">
          Upload histology patches, choose a stain shift condition, and run prediction to inspect real model outputs.
        </p>
      </div>
    );
  }

  if (result.status === "error") {
    return (
      <div className="p-6 bg-red-50/50 rounded-2xl border border-red-200 space-y-3">
        <div className="flex items-center gap-2 text-red-700 font-bold text-sm">
          <AlertTriangle className="w-4 h-4 text-red-600" />
          <span>Inference Error: {result.filename}</span>
        </div>
        <p className="text-xs text-red-600 font-mono bg-white p-3 rounded-lg border border-red-200">
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
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-6">
      {/* Result Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-4">
        <div>
          <span className="text-xs font-mono font-bold text-brand-700 uppercase tracking-wider block">
            {result.filename}
          </span>
          <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
            {result.original_dimensions && (
              <span>{result.original_dimensions[0]}×{result.original_dimensions[1]} px</span>
            )}
            <span>•</span>
            <span className="capitalize">{result.condition_applied.replace(/_/g, " ")} ({result.intensity_applied.toFixed(2)}x)</span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-400" />
              {primaryPred.inference_time_ms.toFixed(2)} ms latency
            </span>
          </div>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center rounded-lg bg-slate-100 p-0.5 text-xs font-medium text-slate-600 self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setViewMode("original")}
            className={`px-2.5 py-1 rounded-md transition ${viewMode === "original" ? "bg-white text-slate-900 shadow-xs font-semibold" : "hover:text-slate-900"}`}
          >
            Original
          </button>
          <button
            type="button"
            onClick={() => setViewMode("transformed")}
            className={`px-2.5 py-1 rounded-md transition ${viewMode === "transformed" ? "bg-white text-slate-900 shadow-xs font-semibold" : "hover:text-slate-900"}`}
          >
            Shifted
          </button>
          <button
            type="button"
            onClick={() => setViewMode("side_by_side")}
            className={`px-2.5 py-1 rounded-md transition ${viewMode === "side_by_side" ? "bg-white text-slate-900 shadow-xs font-semibold" : "hover:text-slate-900"}`}
          >
            Side-by-Side
          </button>
        </div>
      </div>

      {/* Image Previews */}
      <div>
        {viewMode === "side_by_side" ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5 text-center">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Original Input Patch
              </span>
              <div className="aspect-square bg-slate-100 rounded-xl overflow-hidden border border-slate-200 shadow-inner flex items-center justify-center">
                {result.original_thumbnail_b64 ? (
                  <img
                    src={result.original_thumbnail_b64}
                    alt="Original Patch"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-xs text-slate-400">Preview Unavailable</span>
                )}
              </div>
            </div>

            <div className="space-y-1.5 text-center">
              <span className="text-[11px] font-bold uppercase tracking-wider text-brand-700">
                Shifted Image ({result.condition_applied.replace(/_/g, " ")})
              </span>
              <div className="aspect-square bg-slate-100 rounded-xl overflow-hidden border border-slate-200 shadow-inner flex items-center justify-center">
                {result.transformed_thumbnail_b64 ? (
                  <img
                    src={result.transformed_thumbnail_b64}
                    alt="Transformed Patch"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-xs text-slate-400">Preview Unavailable</span>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-xs mx-auto aspect-square bg-slate-100 rounded-xl overflow-hidden border border-slate-200 shadow-inner">
            <img
              src={viewMode === "original" ? (result.original_thumbnail_b64 || "") : (result.transformed_thumbnail_b64 || "")}
              alt={viewMode === "original" ? "Original Patch" : "Shifted Patch"}
              className="w-full h-full object-cover"
            />
          </div>
        )}
      </div>

      {/* Model Comparison Card (if compare mode was run) */}
      {hasBoth && (
        <div className="p-4 rounded-xl border border-indigo-100 bg-indigo-50/30 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-indigo-900 uppercase tracking-wider">
              Model Comparison (Same Input & Shift)
            </span>
            {result.agreement ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                <CheckCircle2 className="w-3.5 h-3.5" /> Models Agree
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800 bg-amber-100 px-2 py-0.5 rounded">
                <AlertTriangle className="w-3.5 h-3.5" /> Prediction Flip Under Shift
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            {/* Baseline Card */}
            <div className="p-3 bg-white rounded-lg border border-slate-200 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-600 flex items-center gap-1">
                  <Cpu className="w-3.5 h-3.5 text-slate-400" /> Baseline Model
                </span>
                <span className="font-mono text-slate-400 text-[10px]">
                  {result.predictions.baseline.inference_time_ms} ms
                </span>
              </div>
              <div className="flex items-baseline justify-between pt-1">
                <span className="text-base font-extrabold text-slate-900">
                  {result.predictions.baseline.predicted_class}
                </span>
                <span className="font-mono text-xs font-bold text-slate-700">
                  {(result.predictions.baseline.confidence * 100).toFixed(1)}% conf
                </span>
              </div>
              <p className="text-[10px] text-slate-500 truncate">
                {result.predictions.baseline.predicted_class_description}
              </p>
            </div>

            {/* Robust Card */}
            <div className="p-3 bg-white rounded-lg border border-brand-200 space-y-1 ring-1 ring-brand-100">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-brand-900 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" /> Stain-Robust Model
                </span>
                <span className="font-mono text-slate-400 text-[10px]">
                  {result.predictions.robust_stain_aug.inference_time_ms} ms
                </span>
              </div>
              <div className="flex items-baseline justify-between pt-1">
                <span className="text-base font-extrabold text-brand-900">
                  {result.predictions.robust_stain_aug.predicted_class}
                </span>
                <span className="font-mono text-xs font-bold text-brand-700">
                  {(result.predictions.robust_stain_aug.confidence * 100).toFixed(1)}% conf
                </span>
              </div>
              <p className="text-[10px] text-slate-500 truncate">
                {result.predictions.robust_stain_aug.predicted_class_description}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Primary Prediction Display */}
      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            {primaryPred.model_name} Prediction
          </span>
          <span className="font-mono text-xs text-slate-400">9-Class Softmax Distribution</span>
        </div>

        <div className="flex items-baseline justify-between">
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
                {primaryPred.predicted_class}
              </span>
              <span className="text-xs font-medium text-slate-600">
                {primaryPred.predicted_class_description}
              </span>
            </div>
          </div>
          <div className="text-right">
            <span className="text-2xl font-mono font-bold text-brand-700">
              {(primaryPred.confidence * 100).toFixed(1)}%
            </span>
            <span className="block text-[10px] text-slate-400">model confidence</span>
          </div>
        </div>

        {/* 9-Class Probability Bar Breakdown */}
        <div className="space-y-1.5 pt-2 border-t border-slate-200/60">
          <span className="text-[11px] font-semibold text-slate-700 block">Class Probabilities:</span>
          <div className="space-y-1">
            {Object.entries(primaryPred.probabilities).map(([cls, prob]) => {
              const pct = (prob * 100).toFixed(1);
              const isWinner = cls === primaryPred.predicted_class;
              const barColor = CLASS_COLORS[cls] || "bg-brand-500";
              return (
                <div key={cls} className="flex items-center gap-2 text-xs">
                  <span className={`w-12 font-mono font-semibold text-[11px] ${isWinner ? "text-slate-900 font-bold" : "text-slate-500"}`}>
                    {cls}
                  </span>
                  <div className="flex-1 h-2.5 bg-slate-200/80 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${barColor} ${isWinner ? "ring-1 ring-slate-900" : "opacity-80"}`}
                      style={{ width: `${Math.max(prob * 100, 0.5)}%` }}
                    />
                  </div>
                  <span className="w-12 text-right font-mono text-[11px] text-slate-600">
                    {pct}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <p className="text-[11px] text-slate-400 italic text-center">
        Research prototype classification only. Softmax confidence does not imply clinical diagnostic certainty.
      </p>
    </div>
  );
}
