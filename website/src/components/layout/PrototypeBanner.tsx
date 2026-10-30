import React from "react";
import { AlertCircle } from "lucide-react";

export function PrototypeBanner() {
  return (
    <div
      role="region"
      aria-label="Research Prototype Notice"
      className="bg-[#FAF4ED] border-b border-[#EDE2D4] px-4 py-2 text-xs text-[#7A4E29] font-normal"
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-[#B26A38] flex-shrink-0" aria-hidden="true" />
          <span>
            <strong className="font-semibold text-[#5E391C]">Research Prototype:</strong> StainShift is an investigational benchmark on synthetic stain variations.
            Not intended, certified, or cleared for clinical diagnostics or patient care.
          </span>
        </div>
        <span className="hidden lg:inline-block px-2.5 py-0.5 bg-[#F0E4D5] text-[#6E4220] text-[11px] rounded-full font-mono">
          CRC-VAL-HE-7K Single-Cohort
        </span>
      </div>
    </div>
  );
}
