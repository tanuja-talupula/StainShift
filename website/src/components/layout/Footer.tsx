import React from "react";
import Link from "next/link";
import { GitBranch, Database, ShieldCheck, ExternalLink } from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-white border-t border-slate-200 mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8 text-sm text-slate-600">
          <div className="md:col-span-2 space-y-3">
            <h2 className="font-bold text-slate-900 text-base">StainShift Histopathology Benchmark</h2>
            <p className="text-slate-600 leading-relaxed text-xs max-w-md">
              A scientifically rigorous evaluation of deep convolutional networks under Hematoxylin and Eosin (H&E)
              staining variations and optical-density perturbations on colorectal adenocarcinoma tissue.
            </p>
            <div className="flex items-center gap-3 text-xs text-slate-500 pt-1">
              <span className="inline-flex items-center gap-1 font-mono">
                <GitBranch className="w-3.5 h-3.5 text-slate-400" />
                Commit: 14ef1e1
              </span>
              <span>•</span>
              <span className="inline-flex items-center gap-1 font-mono">
                <Database className="w-3.5 h-3.5 text-slate-400" />
                CRC-VAL-HE-7K
              </span>
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-slate-900 mb-3 text-xs uppercase tracking-wider">Resources</h3>
            <ul className="space-y-2 text-xs">
              <li>
                <a
                  href="https://github.com/tanuja-talupula/StainShift"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-brand-600 transition"
                >
                  GitHub Repository <ExternalLink className="w-3 h-3 text-slate-400" />
                </a>
              </li>
              <li>
                <a
                  href="https://zenodo.org/records/1214456"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-brand-600 transition"
                >
                  Zenodo Dataset Record <ExternalLink className="w-3 h-3 text-slate-400" />
                </a>
              </li>
              <li>
                <a href="/data/stainshift_results.json" download="stainshift_results.json" className="hover:text-brand-600 transition">
                  Public Results JSON Export
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-slate-900 mb-3 text-xs uppercase tracking-wider">Scientific Disclaimer</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Research prototype only. Tested on 1,077 held-out patches from a single cohort. External multi-center clinical validation is required before diagnostic consideration.
            </p>
          </div>
        </div>

        <div className="border-t border-slate-100 pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-3">
          <p>© 2026 StainShift Research Benchmark. Open source under MIT License.</p>
          <div className="flex items-center gap-2 text-slate-500">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Frozen split manifest SHA-256 verified</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
