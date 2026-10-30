import React from "react";
import { ExternalLink } from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-[#FAF8F5] border-t border-[#E8E4DD] mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-charcoal-500">
          <p className="font-serif text-sm text-charcoal-800">
            StainShift — Evaluating CNN robustness under H&E stain variations.
          </p>
          <div className="flex items-center gap-4 text-xs">
            <a
              href="https://github.com/tanuja-talupula/StainShift"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 hover:text-charcoal-900 transition"
            >
              <span>GitHub</span>
              <ExternalLink className="w-3 h-3 text-charcoal-400" />
            </a>
            <span>•</span>
            <span className="text-charcoal-400">MIT License</span>
            <span>•</span>
            <span className="text-charcoal-400">Research Prototype</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
