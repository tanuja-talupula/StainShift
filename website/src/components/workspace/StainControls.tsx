"use client";

import React from "react";
import { Sliders } from "lucide-react";

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
          <label className="text-xs font-semibold uppercase tracking-wider text-charcoal-700">
            2. Stain Shift Condition
          </label>
        </div>

        <select
          value={selectedCondition}
          onChange={(e) => onSelectCondition(e.target.value)}
          className="w-full px-3.5 py-2.5 rounded-xl border border-[#E8E4DD] bg-white text-xs font-medium text-charcoal-900 shadow-sm focus:outline-none focus:ring-1 focus:ring-[#CC785C] transition"
        >
          {STAIN_CONDITIONS.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>

        <p className="text-[11px] text-charcoal-500">
          {STAIN_CONDITIONS.find((c) => c.id === selectedCondition)?.desc}
        </p>
      </div>

      {/* Intensity Slider — Hidden completely when Original condition is selected */}
      {!isOriginal && (
        <div className="space-y-2 pt-2 border-t border-[#E8E4DD]/60">
          <div className="flex items-center justify-between text-xs">
            <label className="font-medium text-charcoal-700 flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-charcoal-400" />
              <span>Shift Intensity</span>
            </label>
            <span className="font-mono text-xs font-semibold text-charcoal-900 px-2 py-0.5 rounded-full bg-[#EDE7DE]">
              {intensity.toFixed(2)}x
            </span>
          </div>

          <div className="space-y-1">
            <input
              type="range"
              min="0.0"
              max="2.0"
              step="0.05"
              value={intensity}
              onChange={(e) => onIntensityChange(parseFloat(e.target.value))}
              aria-label="Stain Shift Intensity Slider"
              className="w-full h-1.5 bg-[#E8E4DD] rounded-lg appearance-none cursor-pointer accent-[#CC785C]"
            />
            <div className="flex justify-between text-[10px] text-charcoal-400 font-mono">
              <span>0.0x (Neutral)</span>
              <span>1.0x (Calibrated)</span>
              <span>2.0x (Severe)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
