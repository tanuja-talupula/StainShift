"use client";

import React from "react";
import { ShieldCheck, Cpu, GitCompare, Info } from "lucide-react";

interface Props {
  selectedModel: "baseline" | "robust_stain_aug" | "compare";
  onSelectModel: (model: "baseline" | "robust_stain_aug" | "compare") => void;
}

export function ModelSelector({ selectedModel, onSelectModel }: Props) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
          1. Select Inference Model
        </label>
        <span className="text-[11px] text-slate-400">Trained MobileNetV3-Small</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {/* Baseline Option */}
        <button
          type="button"
          onClick={() => onSelectModel("baseline")}
          className={`p-3 rounded-xl border text-left transition flex flex-col justify-between ${
            selectedModel === "baseline"
              ? "border-brand-600 bg-brand-50/50 ring-1 ring-brand-600"
              : "border-slate-200 bg-white hover:border-slate-300"
          }`}
        >
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900">Baseline Model</span>
              <Cpu className="w-3.5 h-3.5 text-slate-400" />
            </div>
            <p className="text-[11px] text-slate-500 mt-1 leading-snug">
              Standard geometric augmentation. Sensitive to stain deviations.
            </p>
          </div>
          <span className="mt-2 text-[10px] font-mono text-slate-400">99.9% clean / 33.9% shifted</span>
        </button>

        {/* Robust Model Option */}
        <button
          type="button"
          onClick={() => onSelectModel("robust_stain_aug")}
          className={`p-3 rounded-xl border text-left transition flex flex-col justify-between ${
            selectedModel === "robust_stain_aug"
              ? "border-brand-600 bg-brand-50/50 ring-1 ring-brand-600"
              : "border-slate-200 bg-white hover:border-slate-300"
          }`}
        >
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-brand-900">Stain-Robust</span>
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            </div>
            <p className="text-[11px] text-slate-500 mt-1 leading-snug">
              Beer-Lambert optical density deconvolution augmentation.
            </p>
          </div>
          <span className="mt-2 text-[10px] font-mono text-emerald-700 font-semibold">98.8% clean / 97.7% shifted</span>
        </button>

        {/* Compare Both Option */}
        <button
          type="button"
          onClick={() => onSelectModel("compare")}
          className={`p-3 rounded-xl border text-left transition flex flex-col justify-between ${
            selectedModel === "compare"
              ? "border-brand-600 bg-brand-50/50 ring-1 ring-brand-600"
              : "border-slate-200 bg-white hover:border-slate-300"
          }`}
        >
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900">Compare Both</span>
              <GitCompare className="w-3.5 h-3.5 text-indigo-500" />
            </div>
            <p className="text-[11px] text-slate-500 mt-1 leading-snug">
              Runs baseline & robust in parallel. Highlights agreement & flips.
            </p>
          </div>
          <span className="mt-2 text-[10px] font-mono text-indigo-700">Side-by-side analysis</span>
        </button>
      </div>
    </div>
  );
}
