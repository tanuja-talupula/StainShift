import React from "react";
import Link from "next/link";
import { GitBranch, Database, ShieldCheck, ExternalLink } from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-[#FAF8F5] border-t border-[#E8E4DD] mt-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10 text-xs text-charcoal-500">
          <div className="md:col-span-2 space-y-3">
            <h2 className="font-serif text-lg font-medium text-charcoal-900">
              StainShift Histopathology Benchmark
            </h2>
            <p className="text-charcoal-500 leading-relaxed max-w-md text-xs">
              A scientifically rigorous evaluation of deep convolutional networks under Hematoxylin and Eosin (H&E)
              staining variations and optical-density perturbations on colorectal adenocarcinoma tissue.
            </p>
            <div className="flex items-center gap-3 text-xs text-charcoal-400 pt-1">
              <span className="inline-flex items-center gap-1 font-mono">
                <GitBranch className="w-3.5 h-3.5 text-charcoal-400" />
                Commit: 14ef1e1
              </span>
              <span>•</span>
              <span className="inline-flex items-center gap-1 font-mono">
                <Database className="w-3.5 h-3.5 text-charcoal-400" />
                CRC-VAL-HE-7K
              </span>
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-charcoal-900 mb-3 text-xs uppercase tracking-wider">Navigation</h3>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/" className="hover:text-charcoal-900 transition">
                  AI Inference Workspace
                </Link>
              </li>
              <li>
                <Link href="/dashboard/" className="hover:text-charcoal-900 transition">
                  Results Dashboard
                </Link>
              </li>
              <li>
                <Link href="/demo/" className="hover:text-charcoal-900 transition">
                  Verified Demo Explorer
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold text-charcoal-900 mb-3 text-xs uppercase tracking-wider">Resources</h3>
            <ul className="space-y-2 text-xs">
              <li>
                <a
                  href="https://github.com/tanuja-talupula/StainShift"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-charcoal-900 transition"
                >
                  GitHub Repository <ExternalLink className="w-3 h-3 text-charcoal-400" />
                </a>
              </li>
              <li>
                <a
                  href="https://zenodo.org/records/1214456"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-charcoal-900 transition"
                >
                  Zenodo Dataset Record <ExternalLink className="w-3 h-3 text-charcoal-400" />
                </a>
              </li>
              <li>
                <a href="/data/stainshift_results.json" download="stainshift_results.json" className="hover:text-charcoal-900 transition">
                  Public Results JSON Export
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-[#E8E4DD] pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-charcoal-400 gap-3">
          <p>© 2026 StainShift Research Benchmark. Open source under MIT License.</p>
          <div className="flex items-center gap-2 text-charcoal-500">
            <ShieldCheck className="w-4 h-4 text-[#2D5A46]" />
            <span>Frozen split manifest SHA-256 verified</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
