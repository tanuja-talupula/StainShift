import React from "react";
import { Terminal, ExternalLink, GitBranch, Database, ShieldCheck, Copy } from "lucide-react";
import { loadBenchmarkDataSync } from "@/lib/loadBenchmark";

export default function ReproductionPage() {
  const data = loadBenchmarkDataSync();

  return (
    <div className="max-w-4xl mx-auto space-y-10">
      <div className="space-y-3">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 text-slate-800 text-xs font-semibold">
          <Terminal className="w-3.5 h-3.5" />
          <span>Complete Reproduction Guide</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Step-by-Step Benchmark Reproduction</h1>
        <p className="text-sm text-slate-600 leading-relaxed">
          Every result, table, and chart on this website can be independently reproduced from scratch using the instructions below.
        </p>
      </div>

      {/* Repository & Dataset Verification Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
        <h3 className="text-base font-bold text-slate-900">1. Provenance & Checksum Verification</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-700">Codebase Git Commit</span>
              <a
                href="https://github.com/tanuja-talupula/StainShift"
                target="_blank"
                rel="noopener noreferrer"
                className="text-brand-600 inline-flex items-center gap-1 hover:underline font-medium"
              >
                GitHub <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <div className="font-mono bg-white p-2 rounded border border-slate-200 text-slate-900 select-all">
              {data.benchmark_metadata.git_commit}
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-700">Zenodo Dataset Record</span>
              <a
                href="https://zenodo.org/records/1214456"
                target="_blank"
                rel="noopener noreferrer"
                className="text-brand-600 inline-flex items-center gap-1 hover:underline font-medium"
              >
                Record 1214456 <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <div className="font-mono bg-white p-2 rounded border border-slate-200 text-slate-900 text-[11px] select-all">
              MD5: 2fd1651b4f94ebd818ebf90ad2b6ce06
            </div>
          </div>
        </div>
      </div>

      {/* Step 2: Environment Setup */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
        <h3 className="text-base font-bold text-slate-900">2. Environment Setup</h3>
        <p className="text-xs text-slate-600">Clone the repository and install dependencies in a clean Python 3.10+ virtual environment:</p>
        <pre className="bg-slate-900 text-slate-100 p-4 rounded-lg font-mono text-xs overflow-x-auto select-all">
{`git clone https://github.com/tanuja-talupula/StainShift.git
cd StainShift
git checkout fix/stainshift-correctness-and-reproducibility

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt`}
        </pre>
      </div>

      {/* Step 3: Dataset Download & Splitting */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
        <h3 className="text-base font-bold text-slate-900">3. Dataset Preparation & Split Freezing</h3>
        <p className="text-xs text-slate-600">Download the official CRC-VAL-HE-7K archive and generate the frozen split manifest:</p>
        <pre className="bg-slate-900 text-slate-100 p-4 rounded-lg font-mono text-xs overflow-x-auto select-all">
{`mkdir -p data && cd data
curl -L -o CRC-VAL-HE-7K.zip "https://zenodo.org/records/1214456/files/CRC-VAL-HE-7K.zip?download=1"
echo "2fd1651b4f94ebd818ebf90ad2b6ce06  CRC-VAL-HE-7K.zip" | md5sum -c
unzip -q CRC-VAL-HE-7K.zip -d CRC-VAL-HE-7K
cd ..

# Freeze 70/15/15 single-cohort split with fixed seed 42
python scripts/freeze_splits.py`}
        </pre>
      </div>

      {/* Step 4: Stage A Training */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
        <h3 className="text-base font-bold text-slate-900">4. Stage A: Model Training & Checkpoint Selection</h3>
        <p className="text-xs text-slate-600">
          Trains both Baseline and Stain-Robust models using only the Train and Validation partitions (5 epochs, batch size 32):
        </p>
        <pre className="bg-slate-900 text-slate-100 p-4 rounded-lg font-mono text-xs overflow-x-auto select-all">
{`python run_experiments.py \\
    --data_dir data/CRC-VAL-HE-7K \\
    --splits_cache data/CRC-VAL-HE-7K/splits.json \\
    --models_dir models/reproduced_benchmark \\
    --exp_dir experiments/reproduced_benchmark \\
    --checkpoint_policy train_new \\
    --stage train_only \\
    --epochs 5 \\
    --batch_size 32 \\
    --device mps \\
    --use_mlflow \\
    --mlflow_tracking_uri sqlite:///mlflow.db \\
    --mlflow_artifact_root ./mlflow_artifacts \\
    --run_type full_experiment`}
        </pre>
      </div>

      {/* Step 5: Stage B Evaluation */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
        <h3 className="text-base font-bold text-slate-900">5. Stage B: Frozen Held-Out Test Evaluation</h3>
        <p className="text-xs text-slate-600">
          Evaluates checkpoints exclusively on the 1,077 held-out test patches across the 8 distinct conditions:
        </p>
        <pre className="bg-slate-900 text-slate-100 p-4 rounded-lg font-mono text-xs overflow-x-auto select-all">
{`python run_experiments.py \\
    --data_dir data/CRC-VAL-HE-7K \\
    --splits_cache data/CRC-VAL-HE-7K/splits.json \\
    --models_dir models/reproduced_benchmark \\
    --exp_dir experiments/reproduced_benchmark \\
    --checkpoint_policy eval_only \\
    --stage eval_only \\
    --device mps \\
    --use_mlflow \\
    --mlflow_tracking_uri sqlite:///mlflow.db \\
    --mlflow_artifact_root ./mlflow_artifacts \\
    --run_type full_experiment`}
        </pre>
      </div>

      {/* Step 6: Public Export & Website Build */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
        <h3 className="text-base font-bold text-slate-900">6. Public Export & Website Verification</h3>
        <pre className="bg-slate-900 text-slate-100 p-4 rounded-lg font-mono text-xs overflow-x-auto select-all">
{`# Export sanitized public JSON and demo examples
python scripts/export_public_benchmark.py
python scripts/export_demo_examples.py

# Run complete test suite (61 tests)
pytest -v

# Build static website
cd website
npm install
npm run build`}
        </pre>
      </div>
    </div>
  );
}
