import React from "react";
import { LatencyProfile } from "@/lib/types";
import { Cpu } from "lucide-react";

interface Props {
  profiles: Record<string, LatencyProfile>;
  disclaimer: string;
}

export function LatencyChart({ profiles, disclaimer }: Props) {
  const mpsBase = profiles["baseline_mps"];
  const mpsRob = profiles["robust_stain_aug_mps"];
  const cpuBase = profiles["baseline_cpu"];

  return (
    <div className="bg-white rounded-2xl border border-[#E8E4DD] p-6 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="font-serif text-lg font-medium text-charcoal-900">Local Device Inference Latency</h3>
          <p className="text-xs text-charcoal-500 mt-0.5">
            Hardware-synchronized execution on Apple Silicon (M-series MPS) vs CPU baseline.
          </p>
        </div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FAF8F5] border border-[#E8E4DD] text-charcoal-700 text-xs font-mono">
          <Cpu className="w-3.5 h-3.5 text-[#CC785C]" />
          <span>Device: Apple Silicon MPS</span>
        </div>
      </div>

      {/* Latency Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#E8E4DD] space-y-1">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-charcoal-400">1. Pure Forward Pass (Batch=1)</div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-serif font-bold font-mono text-charcoal-900">
              {mpsBase?.model_forward_batch1.mean_ms.toFixed(2)} ms
            </span>
            <span className="text-xs text-charcoal-500">mean</span>
          </div>
          <p className="text-[11px] text-charcoal-500 pt-1 leading-snug">
            Timing boundary: Pre-loaded GPU tensor forward evaluation with <code>torch.mps.synchronize()</code>. (median: {mpsBase?.model_forward_batch1.median_ms.toFixed(2)} ms, p95: {mpsBase?.model_forward_batch1.p95_ms.toFixed(2)} ms).
          </p>
        </div>

        <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#E8E4DD] space-y-1">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-charcoal-400">2. Preproc + Forward (Original)</div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-serif font-bold font-mono text-charcoal-900">
              {mpsBase?.preprocessing_inclusive_original.mean_ms.toFixed(2)} ms
            </span>
            <span className="text-xs text-charcoal-500">mean</span>
          </div>
          <p className="text-[11px] text-charcoal-500 pt-1 leading-snug">
            PIL file read from disk + ImageNet transform + host-to-device memory transfer + model forward pass (p95: {mpsBase?.preprocessing_inclusive_original.p95_ms.toFixed(2)} ms).
          </p>
        </div>

        <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#E8E4DD] space-y-1">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-charcoal-400">3. Preproc + Forward (Heavy H)</div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-serif font-bold font-mono text-charcoal-900">
              {mpsBase?.preprocessing_inclusive_heavy_hematoxylin.mean_ms.toFixed(2)} ms
            </span>
            <span className="text-xs text-charcoal-500">mean</span>
          </div>
          <p className="text-[11px] text-charcoal-500 pt-1 leading-snug">
            Macenko Beer-Lambert stain deconvolution + optical density perturbation + model forward pass (p95: {mpsBase?.preprocessing_inclusive_heavy_hematoxylin.p95_ms.toFixed(2)} ms).
          </p>
        </div>
      </div>

      {/* Latency Comparison Table */}
      <div className="overflow-x-auto border border-[#E8E4DD] rounded-xl">
        <table className="w-full text-xs text-left text-charcoal-700">
          <thead className="bg-[#FAF8F5] border-b border-[#E8E4DD] text-charcoal-500 font-medium">
            <tr>
              <th scope="col" className="py-2.5 px-3">Hardware / Execution Target</th>
              <th scope="col" className="py-2.5 px-3 text-right">Forward Batch 1 (Mean)</th>
              <th scope="col" className="py-2.5 px-3 text-right">Forward Batch 1 (Median)</th>
              <th scope="col" className="py-2.5 px-3 text-right">Forward Batch 1 (p95)</th>
              <th scope="col" className="py-2.5 px-3 text-right">Batch 16 Throughput</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E8E4DD] font-mono text-[11px]">
            <tr className="hover:bg-[#FAF8F5] transition">
              <td className="py-2.5 px-3 font-sans font-medium text-charcoal-900">Baseline (Apple Silicon MPS)</td>
              <td className="py-2.5 px-3 text-right">{mpsBase?.model_forward_batch1.mean_ms.toFixed(2)} ms</td>
              <td className="py-2.5 px-3 text-right">{mpsBase?.model_forward_batch1.median_ms.toFixed(2)} ms</td>
              <td className="py-2.5 px-3 text-right">{mpsBase?.model_forward_batch1.p95_ms.toFixed(2)} ms</td>
              <td className="py-2.5 px-3 text-right font-bold text-charcoal-900">
                {mpsBase?.batched_throughput_batch16?.samples_per_second ? `${mpsBase.batched_throughput_batch16.samples_per_second.toFixed(1)} img/s` : "N/A"}
              </td>
            </tr>
            <tr className="hover:bg-[#FAF8F5] transition">
              <td className="py-2.5 px-3 font-sans font-medium text-charcoal-900">Robust Model (Apple Silicon MPS)</td>
              <td className="py-2.5 px-3 text-right">{mpsRob?.model_forward_batch1.mean_ms.toFixed(2)} ms</td>
              <td className="py-2.5 px-3 text-right">{mpsRob?.model_forward_batch1.median_ms.toFixed(2)} ms</td>
              <td className="py-2.5 px-3 text-right">{mpsRob?.model_forward_batch1.p95_ms.toFixed(2)} ms</td>
              <td className="py-2.5 px-3 text-right font-bold text-charcoal-900">
                {mpsRob?.batched_throughput_batch16?.samples_per_second ? `${mpsRob.batched_throughput_batch16.samples_per_second.toFixed(1)} img/s` : "N/A"}
              </td>
            </tr>
            <tr className="hover:bg-[#FAF8F5] transition">
              <td className="py-2.5 px-3 font-sans font-medium text-charcoal-500">Baseline (CPU Reference)</td>
              <td className="py-2.5 px-3 text-right text-charcoal-500">{cpuBase?.model_forward_batch1.mean_ms.toFixed(2)} ms</td>
              <td className="py-2.5 px-3 text-right text-charcoal-500">{cpuBase?.model_forward_batch1.median_ms.toFixed(2)} ms</td>
              <td className="py-2.5 px-3 text-right text-charcoal-500">{cpuBase?.model_forward_batch1.p95_ms.toFixed(2)} ms</td>
              <td className="py-2.5 px-3 text-right text-charcoal-500">
                {cpuBase?.batched_throughput_batch16?.samples_per_second ? `${cpuBase.batched_throughput_batch16.samples_per_second.toFixed(1)} img/s` : "N/A"}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-[11px] text-charcoal-400 italic">
        {disclaimer}
      </p>
    </div>
  );
}
