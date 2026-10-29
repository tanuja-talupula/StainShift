import React from "react";
import { Eye, ShieldCheck, AlertCircle } from "lucide-react";
import { loadDemoManifestSync } from "@/lib/loadDemoData";
import { DemoExplorer } from "@/components/demo/DemoExplorer";

export default function DemoPage() {
  const manifest = loadDemoManifestSync();

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="space-y-3">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 text-xs font-semibold">
          <Eye className="w-3.5 h-3.5" />
          <span>Option B Demonstration</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Verified Precomputed Example Explorer
        </h1>
        <p className="text-xs sm:text-sm text-slate-600 max-w-3xl leading-relaxed">
          Inspect actual model outputs on the first lexicographically sorted held-out test patches per class.
          Deterministic selection provides reproducible inspection, but does not imply an unbiased or representative sample.
          Every probability bar, classification prediction, and correctness indicator is generated from the Stage A
          weights with <strong>zero synthetic logits or browser-side approximation</strong>.
        </p>
      </div>

      {/* Explorer Component */}
      <DemoExplorer manifest={manifest} />
    </div>
  );
}
