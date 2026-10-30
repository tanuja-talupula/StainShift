import React from "react";
import { Download, Database, Cpu, ShieldCheck, ChevronDown } from "lucide-react";
import { loadBenchmarkDataSync } from "@/lib/loadBenchmark";
import { AccuracyComparisonChart } from "@/components/charts/AccuracyComparisonChart";
import { ConfusionMatrixViewer } from "@/components/charts/ConfusionMatrixViewer";
import { LatencyChart } from "@/components/charts/LatencyChart";
import { TechnicalSpecsDrawer } from "@/components/dashboard/TechnicalSpecsDrawer";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export default function DashboardPage() {
  const data = loadBenchmarkDataSync();

  const origRow = data.comparison_table.find((r) => r.condition === "original");
  const deconvRow = data.comparison_table.find((r) => r.condition === "reconstruction_only");

  return (
    <div className="space-y-12">
      {/* Dashboard Header */}
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-[#E8E4DD] pb-8">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-[#EDE7DE] text-charcoal-700 text-xs font-medium">
              Stage B Verified Benchmark
            </span>
            <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-normal text-charcoal-900 tracking-tight leading-tight">
              Verified Benchmark Results Dashboard
            </h1>
            <p className="text-sm sm:text-base text-charcoal-600 max-w-2xl leading-relaxed">
              Evaluated on the frozen held-out test split of <strong>CRC-VAL-HE-7K</strong> (N = 1,077 unexposed patches).
              Examining empirical risk minimization failure modes and physics-informed recovery.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <a
              href="/data/stainshift_results.json"
              download="stainshift_results.json"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-white border border-[#E8E4DD] hover:bg-[#F7F4EE] text-charcoal-800 text-xs font-medium shadow-sm transition"
            >
              <Download className="w-3.5 h-3.5 text-charcoal-500" />
              <span>Public Results JSON</span>
            </a>
          </div>
        </div>

        {/* Compact provenance strip (no Git/MLflow clutter) */}
        <div className="p-4 rounded-2xl bg-[#F5F2EB] border border-[#E8E4DD] text-xs text-charcoal-600 flex flex-wrap gap-6 items-center">
          <div className="flex items-center gap-2.5">
            <Database className="w-4 h-4 text-[#CC785C] flex-shrink-0" />
            <div>
              <span className="text-charcoal-400 block text-[10px] uppercase font-semibold">Dataset</span>
              <span className="font-medium text-charcoal-900">CRC-VAL-HE-7K (7,180 total)</span>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <Cpu className="w-4 h-4 text-[#CC785C] flex-shrink-0" />
            <div>
              <span className="text-charcoal-400 block text-[10px] uppercase font-semibold">Hardware</span>
              <span className="font-medium text-charcoal-900">Apple Silicon MPS</span>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-4 h-4 text-[#2D5A46] flex-shrink-0" />
            <div>
              <span className="text-charcoal-400 block text-[10px] uppercase font-semibold">Status</span>
              <span className="font-medium text-[#2D5A46]">SHA-256 Verified · Frozen Split</span>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white rounded-2xl border border-[#E8E4DD] p-5 shadow-sm space-y-1.5">
          <span className="text-[10px] uppercase font-bold tracking-wider text-charcoal-400">Original H&E Accuracy</span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-serif font-bold text-charcoal-900">
              {origRow?.baseline_accuracy_pct.toFixed(2)}%
            </span>
            <span className="text-xs font-mono font-semibold text-charcoal-700 bg-[#F3EFEA] px-2.5 py-0.5 rounded-full border border-[#E8E4DD]">
              Robust: {origRow?.robust_accuracy_pct.toFixed(2)}%
            </span>
          </div>
          <p className="text-[11px] text-charcoal-500 pt-1 leading-snug">
            Native unperturbed patches. Robust model gives up −1.11 pp on clean data.
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-[#F2D6D6] p-5 shadow-sm space-y-1.5 bg-[#FAF5F5]">
          <span className="text-[10px] uppercase font-bold tracking-wider text-[#9B2A2A]">Reconstruction Control</span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-serif font-bold text-[#9B2A2A]">
              {deconvRow?.baseline_accuracy_pct.toFixed(2)}%
            </span>
            <span className="text-xs font-mono font-bold text-[#2D5A46] bg-[#EDF4EF] px-2.5 py-0.5 rounded-full border border-[#D5E5DA]">
              Robust: {deconvRow?.robust_accuracy_pct.toFixed(2)}%
            </span>
          </div>
          <p className="text-[11px] text-[#9B2A2A] pt-1 leading-snug">
            Baseline collapses under deconvolution without dye change (<strong className="font-bold">−66.02%</strong>).
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-[#D5E5DA] p-5 shadow-sm space-y-1.5 bg-[#F6FAF7]">
          <span className="text-[10px] uppercase font-bold tracking-wider text-[#2D5A46]">Robust Model Recovery</span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-serif font-bold text-[#2D5A46]">
              +{deconvRow?.net_recovery_pct.toFixed(2)}%
            </span>
            <span className="text-xs font-mono text-charcoal-500">Max shift recovery</span>
          </div>
          <p className="text-[11px] text-[#244737] pt-1 leading-snug">
            Beer-Lambert stain augmentation restores high tissue classification accuracy.
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-[#E8E4DD] p-5 shadow-sm space-y-1.5">
          <span className="text-[10px] uppercase font-bold tracking-wider text-charcoal-400">MPS Forward Latency (Batch 1)</span>
          <div className="flex items-baseline justify-between">
            <div className="flex items-baseline gap-1.5">
              <span className="text-2xl font-serif font-bold text-charcoal-900">
                {data.latency_benchmarks.profiles.baseline_mps?.model_forward_batch1.mean_ms.toFixed(2)} ms
              </span>
              <span className="text-[11px] font-mono text-charcoal-400">mean</span>
            </div>
            <span className="text-xs font-mono text-charcoal-600 bg-[#F3EFEA] px-2.5 py-0.5 rounded-full border border-[#E8E4DD]">
              p95: {data.latency_benchmarks.profiles.baseline_mps?.model_forward_batch1.p95_ms.toFixed(2)} ms
            </span>
          </div>
          <p className="text-[11px] text-charcoal-500 pt-1 leading-snug">
            Pure model forward pass on pre-loaded device tensor.
          </p>
        </div>
      </div>

      {/* Main Accuracy Comparison Chart (keep — strongest visual) */}
      <AccuracyComparisonChart data={data.comparison_table} />

      {/* Interactive Confusion Matrix (keep — interactive proof) */}
      <ConfusionMatrixViewer
        baselineResults={data.results.baseline}
        robustResults={data.results.robust_stain_aug}
        conditions={data.conditions_evaluated}
        classNames={data.dataset_metadata.class_names}
      />

      {/* Latency Section (keep — hardware story) */}
      <LatencyChart
        profiles={data.latency_benchmarks.profiles}
        disclaimer={data.latency_benchmarks.disclaimer}
      />

      {/* Technical Specs Drawer (SHA-256, Git, MLflow — moved here from top) */}
      <TechnicalSpecsDrawer data={data} />

      {/* Launch workspace CTA */}
      <div className="rounded-2xl bg-charcoal-900 px-8 py-10 flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="space-y-1.5">
          <h3 className="font-serif text-xl font-medium text-white">
            Ready to test the model live?
          </h3>
          <p className="text-sm text-charcoal-300">
            Upload your own histology patches and run inference in real time.
          </p>
        </div>
        <Link
          href="/workspace/"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-[#CC785C] hover:bg-[#B96449] text-white text-sm font-semibold whitespace-nowrap transition shadow-warm-md"
        >
          Launch AI Workspace
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}
