import React from "react";
import { AlertOctagon, ShieldAlert, Cpu, EyeOff, Scale, HelpCircle } from "lucide-react";

export default function LimitationsPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-10">
      <div className="space-y-3">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-50 text-red-700 text-xs font-semibold">
          <AlertOctagon className="w-3.5 h-3.5" />
          <span>Scientific Caveats & Scope</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Benchmark Limitations & Boundary Conditions</h1>
        <p className="text-sm text-slate-600 leading-relaxed">
          Transparent scientific reporting of experimental boundaries, dataset constraints, and diagnostic disclaimers.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Limitation 1 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
          <div className="w-9 h-9 rounded-lg bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-700">
            <EyeOff className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-slate-900">Synthetic Shifts vs. Real Hospital Variation</h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            The benchmark stain perturbations are generated mathematically using Macenko deconvolution and Beer-Lambert dye scaling.
            While mathematically grounded, synthetic manipulations do not capture the full complexity of real-world multi-center hospital variation,
            such as optical defocus, tissue folds, slide pen markings, variable section thickness, or non-linear illumination shading.
          </p>
        </div>

        {/* Limitation 2 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
          <div className="w-9 h-9 rounded-lg bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-700">
            <Scale className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-slate-900">Single-Cohort, Image-Level Partition</h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Evaluation is conducted on 1,077 held-out patches derived from the single CRC-VAL-HE-7K cohort. Because patient-level identifiers
            are not provided in the public Zenodo record, the split is deterministic at the <em>image patch level</em> rather than the <em>patient level</em>.
            Performance cannot be extrapolated to patient-level diagnosis or external hospital cohorts without prospective validation.
          </p>
        </div>

        {/* Limitation 3 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
          <div className="w-9 h-9 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-700">
            <HelpCircle className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-slate-900">Robust Model Tradeoff (Original Image Accuracy)</h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            The stain-augmented robust model is <strong>not universally superior</strong> across every evaluation dimension.
            On unperturbed, standard native H&E patches, the robust model achieves <strong>98.79%</strong> accuracy compared to the baseline&apos;s <strong>99.91%</strong>
            (a modest tradeoff of $-1.11$ percentage points). Users must weigh this minor clean-data accuracy penalty against the vast $+63.79\%$ gain under domain shift.
          </p>
        </div>

        {/* Limitation 4 */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
          <div className="w-9 h-9 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-700">
            <Cpu className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-slate-900">Hardware Latency Boundaries</h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            All latency figures reported on this site represent local on-device hardware execution on an Apple Silicon M-series chip with MPS acceleration.
            These timings reflect raw tensor forward passes (3.7 to 3.9 ms) and deconvolution preprocessing (11 ms), and must not be conflated
            with web application response times or cloud API network latency.
          </p>
        </div>
      </div>

      {/* Class Support Caveat */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
        <h3 className="text-base font-bold text-slate-900">Class Imbalance & Small Subgroup Support (Debris: $N = 51$)</h3>
        <p className="text-xs text-slate-600 leading-relaxed">
          While the held-out test split totals 1,077 patches, the distribution across the nine histological classes is uneven.
          Specifically, the Debris (<code>DEB</code>) class contains only 51 held-out test patches ($4.7\%$). Individual class precision and recall
          for <code>DEB</code> carry wider binomial confidence intervals than well-represented classes such as Tumor Epithelium (<code>TUM</code>, 185 patches)
          or Adipose Tissue (<code>ADI</code>, 201 patches).
        </p>
      </div>

      {/* Primary Regulatory Disclaimer */}
      <div className="p-6 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-950 flex items-start gap-4 text-xs">
        <ShieldAlert className="w-6 h-6 text-amber-700 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="font-bold text-sm">Regulatory & Clinical Diagnostic Disclaimer</h4>
          <p className="leading-relaxed">
            StainShift is an investigative benchmarking tool developed for research and educational purposes. It is not an approved medical device,
            is not cleared by regulatory agencies (FDA, EMA), and must not be used for primary diagnosis, patient triage, or clinical treatment planning.
          </p>
        </div>
      </div>
    </div>
  );
}
