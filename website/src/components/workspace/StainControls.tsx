"use client";

import React from "react";
import { Sliders, Sparkles, AlertCircle } from "lucide-react";

export const STAIN_CONDITIONS = [
  { id: "original", name: "Original (Unperturbed)", desc: "Exact native RGB pixels without deconvolution loss" },
  { id: "reconstruction_only", name: "Reconstruction Only", desc: "Macenko deconvolution control (evaluates inversion loss)" },
  { id: "heavy_hematoxylin", name: "Heavy Hematoxylin", desc: "Dark hyperchromatic nuclei bias (alpha_h=1.65)" },
  { id: "heavy_eosin", name: "Heavy Eosin", desc: "Vivid pink cytoplasm/stroma dominance (alpha_e=1.65)" },
  { id: "pale_understained", name: "Pale Understained", desc: "Low dye concentration & weak optical density" },
  { id: "dark_overstained", name: "Dark Overstained", desc: "High global dye absorption & dense staining" },
  { id: "synthetic_warm_shift", name: "Synthetic Warm Shift", desc: "Eosin expansion with positive optical rotation (+8°)" },
  { id: "synthetic_cool_shift", name: "Synthetic Cool Shift", desc: "Hematoxylin bias with negative optical rotation (-8°)" },
];

interface Props {
  selectedCondition: string;
  onSelectCondition: (cond: string) => void;
  intensity: number;
  onIntensityChange: (val: number) => void;
}

export function StainControls({
  selectedCondition,
  onSelectCondition,
  intensity,
  onIntensityChange,
}: Props) {
  const isOriginal = selectedCondition === "original";

  return (
    <div className="space-y-4">
      {/* Condition Selector */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
            2. Stain Shift Condition
          </label>
          <span className="text-[11px] text-slate-400">Physics-Based Simulation</span>
        </div>

        <select
          value={selectedCondition}
          onChange={(e) => onSelectCondition(e.target.value)}
          className="w-full px-3 py-2 rounded-xl border border-slate-300 bg-white text-xs font-medium text-slate-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {STAIN_CONDITIONS.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>

        <p className="text-[11px] text-slate-500">
          {STAIN_CONDITIONS.find((c) => c.id === selectedCondition)?.desc}
        </p>
      </div>

      {/* Intensity Slider */}
      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
            <Sliders className="w-3.5 h-3.5 text-brand-600" />
            <span>Shift Intensity Strength</span>
          </div>
          <span className="font-mono text-xs font-bold text-brand-700 bg-white px-2 py-0.5 rounded border border-slate-200">
            {isOriginal ? "N/A" : `${intensity.toFixed(2)}x`}
          </span>
        </div>

        <input
          type="range"
          min="0.0"
          max="2.0"
          step="0.05"
          value={intensity}
          disabled={isOriginal}
          onChange={(e) => onIntensityChange(parseFloat(e.target.value))}
          className={`w-full accent-brand-600 cursor-pointer ${
            isOriginal ? "opacity-40 cursor-not-allowed" : ""
          }`}
          aria-label="Stain Shift Intensity Slider"
        />

        <div className="flex justify-between text-[10px] text-slate-400 font-mono">
          <span>0.0x (Neutral)</span>
          <span>1.0x (Benchmark Calibration)</span>
          <span>2.0x (Severe Shift)</span>
        </div>

        {isOriginal ? (
          <p className="text-[10px] text-slate-400 italic">
            Intensity disabled for Original condition (exact unperturbed pixels).
          </p>
        ) : (
          <p className="text-[10px] text-slate-500 leading-snug">
            Scales concentration factors (alpha_H, alpha_E) and angle rotation. Values other than 1.0x represent interactive experimental variants beyond the fixed benchmark.
          </p>
        )}
      </div>
    </div>
  );
}
