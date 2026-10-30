import React from "react";
import { Eye } from "lucide-react";
import { loadDemoManifestSync } from "@/lib/loadDemoData";
import { DemoExplorer } from "@/components/demo/DemoExplorer";

export default function DemoPage() {
  const manifest = loadDemoManifestSync();

  return (
    <div className="space-y-10">
      {/* Page Header */}
      <div className="space-y-3 border-b border-[#E8E4DD] pb-8">
        <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-[#EDE7DE] text-charcoal-700 text-xs font-medium">
          <Eye className="w-3.5 h-3.5 text-[#CC785C]" />
          <span>Interactive Demo</span>
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-normal text-charcoal-900 tracking-tight leading-tight">
          Demo Explorer
        </h1>
        <p className="text-sm sm:text-base text-charcoal-600 max-w-2xl leading-relaxed">
          Explore 72 pre-evaluated tissue patches across all 8 stain conditions instantly.
          Compare how standard training versus stain-robust augmentation behaves on diverse colorectal histology.
        </p>
      </div>

      {/* Explorer Component */}
      <DemoExplorer manifest={manifest} />
    </div>
  );
}
