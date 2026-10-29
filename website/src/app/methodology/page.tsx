import React from "react";
import { BookOpen, Layers, Cpu, Divide, CheckCircle2 } from "lucide-react";
import { loadBenchmarkDataSync } from "@/lib/loadBenchmark";

export default function MethodologyPage() {
  const data = loadBenchmarkDataSync();

  return (
    <div className="max-w-4xl mx-auto space-y-12">
      <div className="space-y-3">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-50 text-brand-700 text-xs font-semibold">
          <BookOpen className="w-3.5 h-3.5" />
          <span>Scientific Protocol</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Methodology & Mathematical Protocol</h1>
        <p className="text-sm text-slate-600 leading-relaxed">
          Standardized benchmarking framework for measuring and mitigating stain-induced domain shift in computational pathology.
        </p>
      </div>

      {/* Section 1: H&E Staining & Physics */}
      <section className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-4">
        <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Layers className="w-5 h-5 text-brand-600" />
          <span>1. The Physics of Hematoxylin & Eosin Staining</span>
        </h2>
        <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
          In clinical histology, tissue sections are stained with two complementary dyes:
        </p>
        <ul className="list-disc list-inside space-y-1 text-xs text-slate-600 pl-2">
          <li>
            <strong>Hematoxylin</strong>: A basic dye that binds negatively charged nucleic acids, imparting deep blue-purple coloration to cell nuclei.
          </li>
          <li>
            <strong>Eosin Y</strong>: An acidic dye that binds positively charged cytoplasmic and extracellular matrix proteins, staining cytoplasm and connective stroma pink.
          </li>
        </ul>
        <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
          According to the <strong>Beer-Lambert Law</strong>, light absorption through an optical path is linear in optical density (OD) space rather than RGB space:
        </p>
        <div className="p-4 rounded-lg bg-slate-900 text-slate-100 font-mono text-xs overflow-x-auto space-y-2">
          <div>OD = -log10(I / I_0) = S · C</div>
          <div className="text-slate-400 text-[11px]">
            where I is transmitted light, I_0 = 255 (background), S is 3x2 stain matrix, and C is 2xN dye concentrations.
          </div>
        </div>
      </section>

      {/* Section 2: Macenko Stain Deconvolution */}
      <section className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-4">
        <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Divide className="w-5 h-5 text-brand-600" />
          <span>2. Macenko Deconvolution & Synthetic Perturbations</span>
        </h2>
        <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
          StainShift uses Macenko stain deconvolution to decompose RGB patches into individual Hematoxylin and Eosin dye concentrations:
        </p>
        <ol className="list-decimal list-inside space-y-2 text-xs text-slate-600 pl-2">
          <li><strong>Optical Density Conversion</strong>: Pixels with optical density below threshold ($0.15$) are masked as background.</li>
          <li><strong>Singular Value Decomposition (SVD)</strong>: SVD on optical density values extracts the 2D plane spanned by the two dyes.</li>
          <li><strong>Angular Projection & Percentile Extrema</strong>: Robust angular percentiles (1st and 99th) define the dye absorption vectors for Hematoxylin and Eosin.</li>
          <li><strong>Concentration Extraction</strong>: Linear least-squares deconvolution yields stain concentrations $C = S^{-1} \cdot OD$.</li>
          <li>
            <strong>Perturbation in Beer-Lambert Space</strong>:
            <div className="font-mono bg-slate-50 border border-slate-200 p-2 my-1 rounded text-slate-800 text-xs">
              C&apos; = [alpha_H · C_H, alpha_E · C_E], &nbsp; S&apos; = R(theta) · S
            </div>
          </li>
          <li><strong>Reconstruction</strong>: Converted back to RGB via <code>I_pert = I_0 · 10^(-S&apos; · C&apos;)</code>.</li>
        </ol>

        <div className="p-3.5 rounded-lg bg-brand-50 border border-brand-100 text-xs text-brand-900 leading-relaxed">
          <strong>The Reconstruction Control Condition (`reconstruction_only`):</strong> Applies Macenko deconvolution and reconstruction with $\alpha_H = 1.0, \alpha_E = 1.0, \theta = 0^\circ$ (zero dye perturbation). This isolates numerical and color reconstruction artifacts from actual dye shifts.
        </div>
      </section>

      {/* Section 3: Dataset & Frozen Split Partitioning */}
      <section className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-4">
        <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-brand-600" />
          <span>3. Dataset & Split Partitioning</span>
        </h2>
        <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
          The benchmark utilizes the official <strong>CRC-VAL-HE-7K</strong> dataset (Kather et al., Zenodo record 1214456), comprising 7,180 non-overlapping uncompressed 8-bit RGB patches ($224 \times 224$ pixels) extracted from colorectal cancer histological slides across 9 tissue classes:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 text-xs">
          {Object.entries(data.dataset_metadata.class_descriptions).map(([code, desc]) => (
            <div key={code} className="p-2.5 rounded bg-slate-50 border border-slate-100 flex items-center gap-2">
              <span className="font-mono font-bold text-slate-800">{code}</span>
              <span className="text-slate-500 text-[11px]">{desc}</span>
            </div>
          ))}
        </div>

        <div className="space-y-2 pt-2">
          <h4 className="font-semibold text-slate-800 text-xs uppercase tracking-wider">Frozen Single-Cohort Partition</h4>
          <p className="text-xs text-slate-600 leading-relaxed">
            The dataset is frozen into a deterministic <strong>70 / 15 / 15 split</strong> with seed $42$:
          </p>
          <div className="grid grid-cols-3 gap-3 text-center text-xs">
            <div className="p-3 rounded bg-slate-50 border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Training Set</span>
              <span className="text-lg font-bold font-mono text-slate-900">{data.dataset_metadata.train_images}</span>
              <span className="text-slate-400 block text-[11px]">(70.00%)</span>
            </div>
            <div className="p-3 rounded bg-slate-50 border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Validation Set</span>
              <span className="text-lg font-bold font-mono text-slate-900">{data.dataset_metadata.val_images}</span>
              <span className="text-slate-400 block text-[11px]">(15.00%)</span>
            </div>
            <div className="p-3 rounded bg-slate-50 border border-brand-200 bg-brand-50/20">
              <span className="text-brand-600 block text-[10px] uppercase font-bold">Held-Out Test Set</span>
              <span className="text-lg font-bold font-mono text-brand-700">{data.dataset_metadata.held_out_test_images}</span>
              <span className="text-brand-600 block text-[11px]">(15.00% Frozen)</span>
            </div>
          </div>
        </div>
      </section>

      {/* Section 4: Timing & Latency Protocol */}
      <section className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-4">
        <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-brand-600" />
          <span>4. Hardware Latency Measurement Protocol</span>
        </h2>
        <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
          Latency measurements are recorded separately from accuracy stress-testing under explicit timing boundaries on local Apple Silicon hardware:
        </p>
        <ul className="list-disc list-inside space-y-1.5 text-xs text-slate-600 pl-2">
          <li><strong>Warmup Runs</strong>: 20 unrecorded passes to prime GPU kernels and CPU caches.</li>
          <li><strong>Timed Trials</strong>: 100 synchronized repetitions using high-resolution monotonic timers.</li>
          <li><strong>Hardware Synchronization</strong>: <code>torch.mps.synchronize()</code> called before and after timing blocks to ensure asynchronous GPU execution is completely finished before recording elapsed milliseconds.</li>
          <li><strong>Reporting</strong>: Mean, standard deviation, median, and 95th percentile (p95) in milliseconds.</li>
        </ul>
      </section>
    </div>
  );
}
