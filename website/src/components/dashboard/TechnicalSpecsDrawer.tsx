"use client";

import React, { useState } from "react";
import { ChevronDown, GitBranch, ShieldCheck } from "lucide-react";
import { StainShiftBenchmark } from "@/lib/types";

interface Props {
  data: StainShiftBenchmark;
}

export function TechnicalSpecsDrawer({ data }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="bg-white rounded-2xl border border-[#E8E4DD] shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-6 py-4 text-left group hover:bg-[#FAF8F5] transition"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="w-4 h-4 text-[#2D5A46]" />
          <span className="font-serif text-base font-medium text-charcoal-900">
            Technical Specs &amp; Cryptographic Hashes
          </span>
          <span className="text-xs text-charcoal-400 font-mono hidden sm:inline">
            Git · MLflow · SHA-256
          </span>
        </div>
        <ChevronDown
          className={`w-4 h-4 text-charcoal-400 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {open && (
        <div className="px-6 pb-6 space-y-6 border-t border-[#E8E4DD]">
          {/* Provenance */}
          <div className="pt-4 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs text-charcoal-600">
            <div className="flex items-start gap-2.5">
              <GitBranch className="w-4 h-4 text-[#CC785C] mt-0.5 flex-shrink-0" />
              <div>
                <span className="text-charcoal-400 block text-[10px] uppercase font-semibold mb-0.5">Git Commit</span>
                <span className="font-mono text-charcoal-900">{data.benchmark_metadata.git_commit}</span>
              </div>
            </div>
            <div className="flex items-start gap-2.5">
              <ShieldCheck className="w-4 h-4 text-[#2D5A46] mt-0.5 flex-shrink-0" />
              <div>
                <span className="text-charcoal-400 block text-[10px] uppercase font-semibold mb-0.5">MLflow Run ID</span>
                <span className="font-mono text-charcoal-900">{data.benchmark_metadata.mlflow_run_id}</span>
              </div>
            </div>
          </div>

          {/* SHA-256 Hashes Table */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-charcoal-500 mb-2">
              Verified Checkpoint &amp; Split Cryptographic Hashes
            </h4>
            <p className="text-xs text-charcoal-400 mb-3">
              Independent verification hashes matching the frozen artifacts stored in MLflow.
            </p>
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
                    <td className="py-2.5 px-3 text-charcoal-600 break-all">{data.dataset_metadata.split_manifest_sha256}</td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-sans font-medium text-charcoal-900">Baseline Checkpoint (baseline.pth)</td>
                    <td className="py-2.5 px-3 font-sans text-charcoal-700">Epoch {data.models.baseline.selected_epoch}</td>
                    <td className="py-2.5 px-3 text-charcoal-700">{data.models.baseline.best_val_f1.toFixed(4)}</td>
                    <td className="py-2.5 px-3 text-charcoal-600 break-all">{data.models.baseline.checkpoint_sha256}</td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-sans font-medium text-charcoal-900">Robust Checkpoint (robust_stain_aug.pth)</td>
                    <td className="py-2.5 px-3 font-sans text-charcoal-700">Epoch {data.models.robust_stain_aug.selected_epoch}</td>
                    <td className="py-2.5 px-3 text-charcoal-700">{data.models.robust_stain_aug.best_val_f1.toFixed(4)}</td>
                    <td className="py-2.5 px-3 text-charcoal-600 break-all">{data.models.robust_stain_aug.checkpoint_sha256}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
