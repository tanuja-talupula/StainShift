import React from "react";
import { LatencyProfile } from "@/lib/types";
import { Cpu, Zap, AlertCircle } from "lucide-react";

interface Props {
  profiles: Record<string, LatencyProfile>;
  disclaimer: string;
}

export function LatencyChart({ profiles, disclaimer }: Props) {
  const mpsBase = profiles["baseline_mps"];
  const mpsRob = profiles["robust_stain_aug_mps"];
  const cpuBase = profiles["baseline_cpu"];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-slate-900">Local Device Inference Latency</h3>
          <p className="text-xs text-slate-500">
            Hardware-synchronized execution on Apple Silicon (M-series MPS) vs CPU baseline.
          </p>
        </div>
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-100 text-slate-700 text-xs font-mono">
          <Cpu className="w-3.5 h-3.5 text-brand-600" />
          <span>Device: Apple Silicon MPS</span>
        </div>
      </div>

      {/* Latency Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 space-y-1">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">1. Pure Forward Pass (Batch=1)</div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-slate-900">
              {mpsBase?.model_forward_batch1.mean_ms.toFixed(2)} ms
            </span>
            <span className="text-xs text-slate-500">mean (median: {mpsBase?.model_forward_batch1.median_ms.toFixed(2)} ms, p95: {mpsBase?.model_forward_batch1.p95_ms.toFixed(2)} ms)</span>
          </div>
          <p className="text-[11px] text-slate-500 pt-1 leading-snug">
            Timing boundary: Pre-loaded GPU tensor forward evaluation with <code>torch.mps.synchronize()</code>.
          </p>
        </div>

        <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 space-y-1">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">2. Preproc + Forward (Original)</div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-slate-900">
              {mpsBase?.preprocessing_inclusive_original.mean_ms.toFixed(2)} ms
            </span>
            <span className="text-xs text-slate-500">mean (p95: {mpsBase?.preprocessing_inclusive_original.p95_ms.toFixed(2)} ms)</span>
          </div>
          <p className="text-[11px] text-slate-500 pt-1 leading-snug">
            PIL file read from disk + ImageNet transform + host-to-device memory transfer + model forward pass.
          </p>
        </div>

        <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 space-y-1">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">3. Preproc + Forward (Heavy H)</div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-slate-900">
              {mpsBase?.preprocessing_inclusive_heavy_hematoxylin.mean_ms.toFixed(2)} ms
            </span>
            <span className="text-xs text-slate-500">mean (p95: {mpsBase?.preprocessing_inclusive_heavy_hematoxylin.p95_ms.toFixed(2)} ms)</span>
          </div>
          <p className="text-[11px] text-slate-500 pt-1 leading-snug">
            Includes online Macenko stain deconvolution (+5.54 ms CPU overhead) before model forward.
          </p>
        </div>
      </div>

      {/* Batched Throughput Highlight */}
      <div className="p-4 rounded-lg bg-brand-50 border border-brand-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-brand-600 flex-shrink-0" />
          <span className="text-slate-800">
            <strong>Batched Model Throughput (Batch Size 16):</strong> {mpsBase?.batched_throughput_batch16.samples_per_second.toLocaleString()} samples/sec on MPS (vs {cpuBase?.batched_throughput_batch16.samples_per_second.toFixed(1)} samples/sec on CPU baseline, ~{((mpsBase?.batched_throughput_batch16.samples_per_second || 0) / (cpuBase?.batched_throughput_batch16.samples_per_second || 1)).toFixed(0)}x speedup).
          </span>
        </div>
        <span className="font-mono text-brand-700 font-semibold whitespace-nowrap">
          {mpsBase?.batched_throughput_batch16.mean_ms_per_batch.toFixed(2)} ms / batch
        </span>
      </div>

      {/* Mandatory Disclaimer */}
      <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-md flex items-start gap-2.5 text-xs text-amber-900">
        <AlertCircle className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong>Timing Boundary Note:</strong> {disclaimer}
        </p>
      </div>

      {/* Accessible Table */}
      <div className="border-t border-slate-100 pt-4">
        <details className="group">
          <summary className="text-xs text-slate-500 hover:text-slate-800 cursor-pointer font-medium select-none">
            View Complete Latency Metrics Table (Mean, Std, Median, p95)
          </summary>
          <div className="overflow-x-auto mt-3">
            <table className="w-full text-xs text-left text-slate-700">
              <thead className="bg-slate-50 text-slate-900 font-semibold border-b border-slate-200">
                <tr>
                  <th scope="col" className="py-2 px-3">Configuration</th>
                  <th scope="col" className="py-2 px-3">Timing Boundary</th>
                  <th scope="col" className="py-2 px-3 text-right">Mean (ms)</th>
                  <th scope="col" className="py-2 px-3 text-right">Std (ms)</th>
                  <th scope="col" className="py-2 px-3 text-right">Median (ms)</th>
                  <th scope="col" className="py-2 px-3 text-right">p95 (ms)</th>
                  <th scope="col" className="py-2 px-3 text-right">Trials</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {Object.entries(profiles).map(([key, prof]) => (
                  <React.Fragment key={key}>
                    <tr className="bg-slate-50/30">
                      <td className="py-1.5 px-3 font-semibold text-slate-900" colSpan={7}>
                        Profile: {key} ({prof.device.toUpperCase()})
                      </td>
                    </tr>
                    <tr>
                      <td className="py-1 px-3 pl-6 text-slate-600 font-sans">Model Forward (Batch=1)</td>
                      <td className="py-1 px-3 text-slate-500 font-sans">model_forward_only</td>
                      <td className="py-1 px-3 text-right">{prof.model_forward_batch1.mean_ms.toFixed(2)}</td>
                      <td className="py-1 px-3 text-right text-slate-400">{prof.model_forward_batch1.std_ms.toFixed(2)}</td>
                      <td className="py-1 px-3 text-right">{prof.model_forward_batch1.median_ms.toFixed(2)}</td>
                      <td className="py-1 px-3 text-right">{prof.model_forward_batch1.p95_ms.toFixed(2)}</td>
                      <td className="py-1 px-3 text-right text-slate-500 font-sans">{prof.model_forward_batch1.timed_runs}</td>
                    </tr>
                    <tr>
                      <td className="py-1 px-3 pl-6 text-slate-600 font-sans">Preproc + Forward (Original)</td>
                      <td className="py-1 px-3 text-slate-500 font-sans">preprocessing_inclusive</td>
                      <td className="py-1 px-3 text-right">{prof.preprocessing_inclusive_original.mean_ms.toFixed(2)}</td>
                      <td className="py-1 px-3 text-right text-slate-400">{prof.preprocessing_inclusive_original.std_ms.toFixed(2)}</td>
                      <td className="py-1 px-3 text-right">{prof.preprocessing_inclusive_original.median_ms.toFixed(2)}</td>
                      <td className="py-1 px-3 text-right">{prof.preprocessing_inclusive_original.p95_ms.toFixed(2)}</td>
                      <td className="py-1 px-3 text-right text-slate-500 font-sans">{prof.preprocessing_inclusive_original.timed_runs}</td>
                    </tr>
                    <tr>
                      <td className="py-1 px-3 pl-6 text-slate-600 font-sans">Preproc + Forward (Heavy H)</td>
                      <td className="py-1 px-3 text-slate-500 font-sans">preprocessing_inclusive</td>
                      <td className="py-1 px-3 text-right">{prof.preprocessing_inclusive_heavy_hematoxylin.mean_ms.toFixed(2)}</td>
                      <td className="py-1 px-3 text-right text-slate-400">{prof.preprocessing_inclusive_heavy_hematoxylin.std_ms.toFixed(2)}</td>
                      <td className="py-1 px-3 text-right">{prof.preprocessing_inclusive_heavy_hematoxylin.median_ms.toFixed(2)}</td>
                      <td className="py-1 px-3 text-right">{prof.preprocessing_inclusive_heavy_hematoxylin.p95_ms.toFixed(2)}</td>
                      <td className="py-1 px-3 text-right text-slate-500 font-sans">{prof.preprocessing_inclusive_heavy_hematoxylin.timed_runs}</td>
                    </tr>
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </div>
    </div>
  );
}
