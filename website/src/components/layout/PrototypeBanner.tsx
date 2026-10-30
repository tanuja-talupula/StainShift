import React from "react";
import { AlertCircle } from "lucide-react";

export function PrototypeBanner() {
  return (
    <aside
      aria-label="Research Prototype Notice"
      className="bg-[#FAF4ED] border-b border-[#EDE2D4] px-4 py-1.5 text-[11px] text-[#7A4E29]"
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5 text-[#CC785C] flex-shrink-0" aria-hidden="true" />
          <span>Research Prototype — For investigational benchmark use only.</span>
        </div>
        <span className="hidden sm:inline text-[10px] text-[#8C5528]/80 font-mono">
          Colorectal Histopathology Evaluation
        </span>
      </div>
    </aside>
  );
}
