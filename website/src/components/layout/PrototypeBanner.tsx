import React from "react";
import { AlertTriangle } from "lucide-react";

export function PrototypeBanner() {
  return (
    <div
      role="region"
      aria-label="Research Prototype Notice"
      className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-2 text-xs md:text-sm text-amber-900 font-medium"
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" aria-hidden="true" />
          <span>
            <strong>Research Prototype:</strong> StainShift is an investigational benchmark on synthetic stain variations.
            Not intended, certified, or cleared for clinical diagnostics or patient care.
          </span>
        </div>
        <span className="hidden lg:inline-block px-2 py-0.5 bg-amber-200/60 text-amber-800 text-[11px] rounded font-mono">
          CRC-VAL-HE-7K Single-Cohort
        </span>
      </div>
    </div>
  );
}
