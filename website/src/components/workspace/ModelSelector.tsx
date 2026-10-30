"use client";

import React from "react";
import { ShieldCheck, Cpu, GitCompare } from "lucide-react";

interface Props {
  selectedModel: "baseline" | "robust_stain_aug" | "compare";
  onSelectModel: (model: "baseline" | "robust_stain_aug" | "compare") => void;
}

export function ModelSelector({ selectedModel, onSelectModel }: Props) {
  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold uppercase tracking-wider text-charcoal-700">
          1. Select Inference Model
        </label>
        <span className="text-[11px] text-charcoal-400 font-mono">MobileNetV3-Small</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        {/* Baseline Option */}
        <button
          type="button"
          onClick={() => onSelectModel("baseline")}
          className={`p-3.5 rounded-2xl border text-left transition flex flex-col justify-between ${
            selectedModel === "baseline"
              ? "border-charcoal-900 bg-[#F4EFEA] shadow-sm ring-1 ring-charcoal-900"
              : "border-[#E8E4DD] bg-white hover:border-[#D5CEC2] hover:bg-[#FAF8F5]"
          }`}
        >
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-charcoal-900">Baseline</span>
              <Cpu className="w-3.5 h-3.5 text-charcoal-400" />
            </div>
            <p className="text-[11px] text-charcoal-500 mt-1 leading-snug">
              Standard geometric augmentation. Sensitive to stain deviations.
            </p>
          </div>
          <span className="mt-2.5 text-[10px] font-mono text-charcoal-400">99.9% clean / 33.9% shifted</span>
        </button>

        {/* Robust Model Option */}
        <button
          type="button"
          onClick={() => onSelectModel("robust_stain_aug")}
          className={`p-3.5 rounded-2xl border text-left transition flex flex-col justify-between ${
            selectedModel === "robust_stain_aug"
              ? "border-charcoal-900 bg-[#F4EFEA] shadow-sm ring-1 ring-charcoal-900"
              : "border-[#E8E4DD] bg-white hover:border-[#D5CEC2] hover:bg-[#FAF8F5]"
          }`}
        >
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-charcoal-900">Stain-Robust</span>
              <ShieldCheck className="w-3.5 h-3.5 text-[#2D5A46]" />
            </div>
            <p className="text-[11px] text-charcoal-500 mt-1 leading-snug">
              Beer-Lambert optical density deconvolution augmentation.
            </p>
          </div>
          <span className="mt-2.5 text-[10px] font-mono text-[#2D5A46] font-semibold">98.8% clean / 97.7% shifted</span>
        </button>

        {/* Compare Both Option */}
        <button
          type="button"
          onClick={() => onSelectModel("compare")}
          className={`p-3.5 rounded-2xl border text-left transition flex flex-col justify-between ${
            selectedModel === "compare"
              ? "border-charcoal-900 bg-[#F4EFEA] shadow-sm ring-1 ring-charcoal-900"
              : "border-[#E8E4DD] bg-white hover:border-[#D5CEC2] hover:bg-[#FAF8F5]"
          }`}
        >
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-charcoal-900">Compare Both</span>
              <GitCompare className="w-3.5 h-3.5 text-[#CC785C]" />
            </div>
            <p className="text-[11px] text-charcoal-500 mt-1 leading-snug">
              Runs baseline & robust in parallel. Highlights agreement & flips.
            </p>
          </div>
          <span className="mt-2.5 text-[10px] font-mono text-[#CC785C] font-semibold">Side-by-side analysis</span>
        </button>
      </div>
    </div>
  );
}
