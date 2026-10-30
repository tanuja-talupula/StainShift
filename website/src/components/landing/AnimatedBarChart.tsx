"use client";

import React, { useEffect, useRef, useState } from "react";
import { ComparisonRow } from "@/lib/types";

interface Props {
  data: ComparisonRow[];
}

const CONDITION_LABELS: Record<string, string> = {
  original: "Original H&E",
  reconstruction_only: "Deconv Control",
  heavy_hematoxylin: "Heavy Hema.",
  heavy_eosin: "Heavy Eosin",
  pale_understained: "Pale Under.",
  dark_overstained: "Dark Over.",
  synthetic_warm_shift: "Synth. Warm",
  synthetic_cool_shift: "Synth. Cool",
};

export function AnimatedBarChart({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setTimeout(() => setAnimated(true), 100);
          observer.unobserve(el);
        }
      },
      { threshold: 0.2 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className="space-y-3">
      {data.map((row, i) => {
        const label = CONDITION_LABELS[row.condition] ?? row.condition.replace(/_/g, " ");
        const bPct = row.baseline_accuracy_pct;
        const rPct = row.robust_accuracy_pct;

        return (
          <div key={row.condition} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-charcoal-700 w-28 shrink-0">{label}</span>
              <span className="text-charcoal-400 font-mono text-[11px]">
                <span className="text-charcoal-500">{bPct.toFixed(1)}%</span>
                <span className="mx-1 text-charcoal-300">→</span>
                <span className="text-[#CC785C] font-bold">{rPct.toFixed(1)}%</span>
              </span>
            </div>

            {/* Baseline bar */}
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#A8A196] shrink-0" />
              <div className="flex-1 h-2.5 bg-[#F3EFEA] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#A8A196] rounded-full"
                  style={{
                    width: animated ? `${bPct}%` : "0%",
                    transition: `width 0.9s cubic-bezier(0.25, 0.46, 0.45, 0.94) ${i * 60}ms`,
                  }}
                />
              </div>
            </div>

            {/* Robust bar */}
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#CC785C] shrink-0" />
              <div className="flex-1 h-2.5 bg-[#F3EFEA] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#CC785C] rounded-full"
                  style={{
                    width: animated ? `${rPct}%` : "0%",
                    transition: `width 0.9s cubic-bezier(0.25, 0.46, 0.45, 0.94) ${i * 60 + 120}ms`,
                  }}
                />
              </div>
            </div>
          </div>
        );
      })}

      {/* Legend */}
      <div className="flex items-center gap-5 pt-2 text-xs text-charcoal-500">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-1.5 rounded-full bg-[#A8A196] inline-block" />
          <span>Standard Baseline</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-1.5 rounded-full bg-[#CC785C] inline-block" />
          <span className="font-semibold text-charcoal-700">Stain-Robust</span>
        </div>
      </div>
    </div>
  );
}
