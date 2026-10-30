import React from "react";
import { Download, Database, GitBranch, Cpu, ShieldCheck } from "lucide-react";
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
      {/* Dashboard Editorial Header */}
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-[#E8E4DD] pb-8">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-[#EDE7DE] text-charcoal-700 text-xs font-medium">
              <span>Stage B Verified Benchmark</span>
            </span>
            <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-normal text-charcoal-900 tracking-tight leading-tight">
              Verified Benchmark Results Dashboard
            </h1>
            <p className="text-sm sm:text-base text-charcoal-600 max-w-2xl leading-relaxed">
              Evaluated on the frozen held-out test split of <strong>CRC-VAL-HE-7K</strong> ($N = 1,077$ unexposed patches).
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

        {/* Provenance Banner */}
        <div className="p-4 rounded-2xl bg-[#F5F2EB] border border-[#E8E4DD] text-xs text-charcoal-600 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="flex items-center gap-2.5">
            <Database className="w-4 h-4 text-[#CC785C] flex-shrink-0" />
            <div>
              <span className="text-charcoal-400 block text-[10px] uppercase font-semibold">Dataset</span>
              <span className="font-medium text-charcoal-900">CRC-VAL-HE-7K (7,180 total)</span>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <GitBranch className="w-4 h-4 text-[#CC785C] flex-shrink-0" />
            <div>
              <span className="text-charcoal-400 block text-[10px] uppercase font-semibold">Git Commit</span>
              <span className="font-mono text-charcoal-900">{data.benchmark_metadata.git_commit.slice(0, 10)}</span>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <Cpu className="w-4 h-4 text-[#CC785C] flex-shrink-0" />
            <div>
              <span className="text-charcoal-400 block text-[10px] uppercase font-semibold">Device</span>
              <span className="font-medium text-charcoal-900">Apple Silicon MPS</span>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-4 h-4 text-[#2D5A46] flex-shrink-0" />
            <div>
              <span className="text-charcoal-400 block text-[10px] uppercase font-semibold">MLflow Run ID</span>
              <span className="font-mono text-charcoal-900">{data.benchmark_metadata.mlflow_run_id.slice(0, 12)}...</span>
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
            Native unperturbed patches. Robust model gives up -1.11 percentage points on clean data.
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
            Baseline collapses under deconvolution without dye change (<strong className="font-bold">-66.02%</strong>).
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
            Beer-Lambert stain augmentation restores high tissue classification accuracy across all synthetic shifts.
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
            Local hardware timing boundary: Pure model forward pass on pre-loaded device tensor.
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
      <div className="bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-sm space-y-4">
        <div>
          <h3 className="font-serif text-lg font-medium text-charcoal-900">Verified Checkpoint & Split Cryptographic Hashes</h3>
          <p className="text-xs text-charcoal-500 mt-0.5">
            Independent verification hashes matching the frozen artifacts stored in MLflow.
          </p>
        </div>

        <div className="overflow-x-auto border border-[#E8E4DD] rounded-xl">
          <table className="w-full text-xs text-left text-charcoal-700">
            <thead className="bg-[#FAF8F5] font-semibold border-b border-[#E8E4DD] text-charcoal-500">
              <tr>
                <th scope="col" className="py-2.5 px-3">Artifact Description</th>
                <th scope="col" className="py-2.5 px-3">Selected Epoch</th>
                <th scope="col" className="py-2.5 px-3">Validation F1</th>
                <th scope="col" className="py-2.5 px-3 font-mono">SHA-256 Checksum</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E4DD] font-mono text-[11px]">
              <tr>
                <td className="py-2.5 px-3 font-sans font-medium text-charcoal-900">Frozen Split Manifest</td>
                <td className="py-2.5 px-3 font-sans text-charcoal-400">—</td>
                <td className="py-2.5 px-3 font-sans text-charcoal-400">—</td>
                <td className="py-2.5 px-3 text-charcoal-600">{data.dataset_metadata.split_manifest_sha256}</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 font-sans font-medium text-charcoal-900">Baseline Checkpoint (baseline.pth)</td>
                <td className="py-2.5 px-3 font-sans text-charcoal-700">Epoch {data.models.baseline.selected_epoch}</td>
                <td className="py-2.5 px-3 text-charcoal-700">{data.models.baseline.best_val_f1.toFixed(4)}</td>
                <td className="py-2.5 px-3 text-charcoal-600">{data.models.baseline.checkpoint_sha256}</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 font-sans font-medium text-charcoal-900">Robust Checkpoint (robust_stain_aug.pth)</td>
                <td className="py-2.5 px-3 font-sans text-charcoal-700">Epoch {data.models.robust_stain_aug.selected_epoch}</td>
                <td className="py-2.5 px-3 text-charcoal-700">{data.models.robust_stain_aug.best_val_f1.toFixed(4)}</td>
                <td className="py-2.5 px-3 text-charcoal-600">{data.models.robust_stain_aug.checkpoint_sha256}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
