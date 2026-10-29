import React from "react";
import Link from "next/link";
import { Download, Database, GitBranch, Cpu, ShieldCheck, AlertCircle } from "lucide-react";
import { loadBenchmarkDataSync } from "@/lib/loadBenchmark";
import { AccuracyComparisonChart } from "@/components/charts/AccuracyComparisonChart";
import { AccuracyDropChart } from "@/components/charts/AccuracyDropChart";
import { MacroF1Chart } from "@/components/charts/MacroF1Chart";
import { LatencyChart } from "@/components/charts/LatencyChart";
import { ConfusionMatrixViewer } from "@/components/charts/ConfusionMatrixViewer";

export default function DashboardPage() {
  const data = loadBenchmarkDataSync();

  const origRow = data.comparison_table.find((r) => r.condition === "original");
  const deconvRow = data.comparison_table.find((r) => r.condition === "reconstruction_only");

  return (
    <div className="space-y-12">
      {/* Dashboard Header & Metadata Provenance Bar */}
      <div className="space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Verified Benchmark Results Dashboard
            </h1>
            <p className="text-xs sm:text-sm text-slate-500">
              Evaluated on the frozen held-out test split of <strong>CRC-VAL-HE-7K</strong> ($N = 1,077$ unexposed patches).
            </p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="/data/stainshift_results.json"
              download="stainshift_results.json"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-sm transition"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>Public Results JSON</span>
            </a>
          </div>
        </div>

        {/* Provenance Banner */}
        <div className="p-3.5 rounded-xl bg-slate-100 border border-slate-200/80 text-xs text-slate-600 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-brand-600 flex-shrink-0" />
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Dataset</span>
              <span className="font-semibold text-slate-900">CRC-VAL-HE-7K (7,180 total)</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-brand-600 flex-shrink-0" />
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Git Commit</span>
              <span className="font-mono text-slate-900">{data.benchmark_metadata.git_commit.slice(0, 10)}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-brand-600 flex-shrink-0" />
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Device</span>
              <span className="font-semibold text-slate-900">Apple Silicon MPS</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-bold">MLflow Run ID</span>
              <span className="font-mono text-slate-900">{data.benchmark_metadata.mlflow_run_id.slice(0, 12)}...</span>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1">
          <span className="text-xs uppercase font-bold tracking-wider text-slate-500">Original H&E Accuracy</span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-extrabold font-mono text-slate-900">
              {origRow?.baseline_accuracy_pct.toFixed(2)}%
            </span>
            <span className="text-xs font-mono font-bold text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
              Robust: {origRow?.robust_accuracy_pct.toFixed(2)}%
            </span>
          </div>
          <p className="text-[11px] text-slate-500 pt-1">
            Native unperturbed patches. Robust model gives up -1.11 percentage points on clean data.
          </p>
        </div>

        <div className="bg-white rounded-xl border border-red-200 p-5 shadow-sm space-y-1 bg-red-50/20">
          <span className="text-xs uppercase font-bold tracking-wider text-red-600">Reconstruction Control</span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-extrabold font-mono text-red-600">
              {deconvRow?.baseline_accuracy_pct.toFixed(2)}%
            </span>
            <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
              Robust: {deconvRow?.robust_accuracy_pct.toFixed(2)}%
            </span>
          </div>
          <p className="text-[11px] text-slate-600 pt-1">
            Baseline collapses under deconvolution without dye change (<strong className="text-red-700">-66.02%</strong>).
          </p>
        </div>

        <div className="bg-white rounded-xl border border-emerald-200 p-5 shadow-sm space-y-1 bg-emerald-50/20">
          <span className="text-xs uppercase font-bold tracking-wider text-emerald-700">Robust Model Recovery</span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-extrabold font-mono text-emerald-700">
              +{deconvRow?.net_recovery_pct.toFixed(2)}%
            </span>
            <span className="text-xs text-slate-500">Max shift recovery</span>
          </div>
          <p className="text-[11px] text-slate-600 pt-1">
            Beer-Lambert stain augmentation restores high tissue classification accuracy across all synthetic shifts.
          </p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-1">
          <span className="text-xs uppercase font-bold tracking-wider text-slate-500">MPS Forward Latency (Batch 1)</span>
          <div className="flex items-baseline justify-between">
            <div className="flex items-baseline gap-1.5">
              <span className="text-2xl font-extrabold font-mono text-slate-900">
                {data.latency_benchmarks.profiles.baseline_mps?.model_forward_batch1.mean_ms.toFixed(2)} ms
              </span>
              <span className="text-[11px] font-mono text-slate-500">mean</span>
            </div>
            <span className="text-xs font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
              Median: {data.latency_benchmarks.profiles.baseline_mps?.model_forward_batch1.median_ms.toFixed(2)} ms
            </span>
          </div>
          <p className="text-[11px] text-slate-500 pt-1">
            Local device execution (p95: {data.latency_benchmarks.profiles.baseline_mps?.model_forward_batch1.p95_ms.toFixed(2)} ms). Pure model forward pass on pre-loaded device tensor.
          </p>
        </div>
      </div>

      {/* Main Accuracy Chart */}
      <AccuracyComparisonChart data={data.comparison_table} />

      {/* Accuracy Drop and Macro F1 Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <AccuracyDropChart data={data.comparison_table} />
        <MacroF1Chart
          baselineResults={data.results.baseline}
          robustResults={data.results.robust_stain_aug}
          conditions={data.conditions_evaluated}
        />
      </div>

      {/* Interactive Confusion Matrix */}
      <ConfusionMatrixViewer
        baselineResults={data.results.baseline}
        robustResults={data.results.robust_stain_aug}
        conditions={data.conditions_evaluated}
        classNames={data.dataset_metadata.class_names}
      />

      {/* Latency Section */}
      <LatencyChart
        profiles={data.latency_benchmarks.profiles}
        disclaimer={data.latency_benchmarks.disclaimer}
      />

      {/* Checkpoint & Split Hashes Table */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
        <h3 className="text-base font-bold text-slate-900">Verified Checkpoint & Split Cryptographic Hashes</h3>
        <p className="text-xs text-slate-500">
          Independent verification hashes matching the frozen artifacts stored in MLflow.
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left text-slate-700">
            <thead className="bg-slate-50 font-semibold border-b border-slate-200">
              <tr>
                <th scope="col" className="py-2.5 px-3">Artifact Description</th>
                <th scope="col" className="py-2.5 px-3">Selected Epoch</th>
                <th scope="col" className="py-2.5 px-3">Validation F1</th>
                <th scope="col" className="py-2.5 px-3 font-mono">SHA-256 Checksum</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              <tr>
                <td className="py-2.5 px-3 font-sans font-medium text-slate-900">Frozen Split Manifest</td>
                <td className="py-2.5 px-3 font-sans text-slate-500">—</td>
                <td className="py-2.5 px-3 font-sans text-slate-500">—</td>
                <td className="py-2.5 px-3 text-slate-600 text-[11px]">{data.dataset_metadata.split_manifest_sha256}</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 font-sans font-medium text-slate-900">Baseline Checkpoint (baseline.pth)</td>
                <td className="py-2.5 px-3 font-sans text-slate-700">Epoch {data.models.baseline.selected_epoch}</td>
                <td className="py-2.5 px-3 text-slate-700">{data.models.baseline.best_val_f1.toFixed(4)}</td>
                <td className="py-2.5 px-3 text-slate-600 text-[11px]">{data.models.baseline.checkpoint_sha256}</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 font-sans font-medium text-slate-900">Robust Checkpoint (robust_stain_aug.pth)</td>
                <td className="py-2.5 px-3 font-sans text-slate-700">Epoch {data.models.robust_stain_aug.selected_epoch}</td>
                <td className="py-2.5 px-3 text-slate-700">{data.models.robust_stain_aug.best_val_f1.toFixed(4)}</td>
                <td className="py-2.5 px-3 text-slate-600 text-[11px]">{data.models.robust_stain_aug.checkpoint_sha256}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
