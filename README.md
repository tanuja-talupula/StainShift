# 🔬 StainShift: Histopathology Stain Domain Shift Benchmark

> **Scientific Scope:** *Investigating classifier behavior under synthetic H&E optical density perturbations.*
>
> ⚠️ **Non-Clinical Research Disclaimer:** StainShift is an exploratory research engineering toolkit. It is **not** a medical device, diagnostic system, or clinical decision support system. Softmax outputs represent model score distributions and must not be interpreted as calibrated clinical certainty or evidence of real-world multi-scanner robustness.

---

## 1. Overview & Research Scope

StainShift models how deep convolutional neural networks respond to synthetic alterations in Hematoxylin and Eosin dye concentrations and stain vector angles using Beer-Lambert optical density deconvolution (Macenko et al., 2009).

### Key Scientific Limitations
1. **Synthetic vs. Real-World Domain Shifts:** Synthetic Beer-Lambert scaling and 2D rotations provide controllable mathematical perturbations. They **do not** fully capture complex non-linear optical artifacts, slide preparation differences, microtome section thickness variations, illumination spectral differences, or scanner sensor response curves.
2. **Patch-Level vs. Patient-Level Splitting:** When metadata for patient slide IDs is not available, random splitting operates at the tile level. While tile disjointness is strictly enforced, intra-patient correlation can exist across tiles from the same subject. Grouped splitting should be used whenever slide/patient IDs are provided.
3. **Historical vs. Verified Checkpoints:** Prior checkpoints produced before the repair of the augmentation pipeline suffered from silent decomposer fallback. Any historical JSON results in `experiments/` represent unverified baseline records; models must be retrained with the corrected pipeline to validate true stain-augmented robustness.

---

## 2. Dataset Acquisition & Expected Structure

StainShift supports the open-access colorectal cancer histopathology benchmarks from Kather et al. ([Zenodo 1214456](https://doi.org/10.5281/zenodo.1214456) & [Zenodo 1214456](https://doi.org/10.5281/zenodo.1214456)):
- `CRC-VAL-HE-7K`: 7,180 non-overlapping tissue tiles ($224 \times 224$ px at $0.5\,\mu\text{m/px}$) across 9 tissue classes from the DACHS cohort.
- `NCT-CRC-HE-100K-NONORM`: 100,000 multi-center tiles from the NCT cohort without stain normalization.

### Expected Directory Hierarchy
```
StainShift/
├── app.py                      # Interactive Streamlit dashboard
├── run_experiments.py          # Master runner for training & stress-testing
├── train_100k_val_7k.py        # Cross-cohort 100K training & 7K validation workflow
├── requirements.txt            # Pinned runtime dependencies
├── requirements-dev.txt        # Development and testing dependencies
├── pyproject.toml              # Build specification and pytest configuration
├── data/                       # Local dataset directory (not tracked in git)
│   ├── CRC-VAL-HE-7K-png/      # <CLASS>-<IDENTIFIER>.png patches
│   └── splits.json             # Stratified split manifest (created automatically)
├── models/                     # Checkpoint directory
│   ├── baseline.pth            # Standard training checkpoint
│   └── robust_stain_aug.pth    # Stain-augmented checkpoint
├── experiments/                # Evaluation output reports and summaries
├── src/                        # Core package
│   ├── dataset.py              # CRCDataset & stratified partition logic
│   ├── models.py               # Model architectures and metadata checkpoint I/O
│   ├── stain_shift.py          # Macenko deconvolution, Reinhard transfer, presets
│   ├── train.py                # Isolated training loop with metadata tracking
│   └── evaluate.py             # Stress-testing, metrics, and failure auditing
└── tests/                      # Comprehensive engineering test suite
```

---

## 3. Installation & Verification

### Setup
```bash
git clone https://github.com/tanuja-talupula/StainShift.git
cd StainShift

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Run Automated Test Suite
The test suite validates data loaders, exact neutral controls, loud failure handling, checkpoint loading, and CLI flags using tiny synthetic fixtures (no external downloads or GPUs required):
```bash
pytest -v
```

---

## 4. Workflows & Command-Line Interfaces

StainShift provides two distinct training and evaluation workflows:

### Workflow A: Single-Cohort Stratified Benchmark (`run_experiments.py`)
Uses `CRC-VAL-HE-7K` partitioned into stratified Train (70%), Validation (15%), and Test (15%) splits:
- **Dry-run configuration check:**
  Performs static path, directory, and CLI argument verification without executing training or evaluation:
  ```bash
  python run_experiments.py --dry-run
  ```
  *(Note: `--dry-run` validates file existence and arguments only; it does not train models, compute training curves, or generate evaluation metric tables).*
- **Bounded Real-Data Smoke Test:**
  Runs an actual 1-epoch, sample-limited execution on real data to test the end-to-end pipeline:
  ```bash
  python run_experiments.py --data_dir data/CRC-VAL-HE-7K-png --epochs 1 --max_samples_per_class 10 --batch_size 16 --use_mlflow --run_type smoke_test
  ```
- **Train and stress-test:**
  ```bash
  python run_experiments.py --data_dir data/CRC-VAL-HE-7K-png --checkpoint_policy train_new --epochs 5 --device cpu
  ```
- **Checkpoint Policy Options:**
  - `train_new`: Forces a fresh training run from scratch.
  - `reuse_if_valid`: Validates checkpoint existence and architecture metadata before running stress tests.
  - `eval_only`: Evaluates existing verified models without training.

### Workflow B: Cross-Cohort Evaluation (`train_100k_val_7k.py`)
Trains on `NCT-CRC-HE-100K-NONORM` and evaluates generalization on `CRC-VAL-HE-7K`:
- **Model Selection Protocol Distinction:**
  - When the 7K cohort is used to select the best checkpoint, it is designated as **external validation used for model selection**, not an untouched final test.
  - Command:
    ```bash
    python train_100k_val_7k.py --train_dir data/NCT-CRC-HE-100K-NONORM-png --val_dir data/CRC-VAL-HE-7K-png --selection_protocol external_val_selection
    ```

---

## 5. Stain Shift Profiles & Transformation Policy

### Evaluated Profiles
| Profile | $\alpha_H$ (Hematoxylin) | $\alpha_E$ (Eosin) | OD Rotation | Description |
| :--- | :---: | :---: | :---: | :--- |
| `original` | 1.00 | 1.00 | $0.0^\circ$ | Exact original source image (pixel bypass) |
| `reconstruction_only` | 1.00 | 1.00 | $0.0^\circ$ | Deconvolution/reconstruction control (lossy OD roundtrip) |
| `heavy_hematoxylin` | 1.65 | 0.85 | $+3.0^\circ$ | Synthetic heavy hematoxylin bias |
| `heavy_eosin` | 0.75 | 1.65 | $-3.0^\circ$ | Synthetic heavy eosin bias |
| `pale_understained`| 0.60 | 0.60 | $0.0^\circ$ | Synthetic reduced dye concentration |
| `dark_overstained` | 1.50 | 1.50 | $0.0^\circ$ | Synthetic high dye concentration |
| `synthetic_warm_shift`| 0.90 | 1.30 | $+8.0^\circ$ | Synthetic warm shift (increased E, positive angle rotation) |
| `synthetic_cool_shift`| 1.35 | 0.80 | $-8.0^\circ$ | Synthetic cool shift (increased H, negative angle rotation) |

*(Legacy aliases `scanner_warm_shift` and `scanner_cool_shift` remain supported for backward compatibility).*

### Transformation Failure Accounting
- When deconvolution encounters numerical issues (insufficient tissue pixels or degenerate optical density covariance), the failure reason and file path are recorded.
- Fallback images are **never** scored as successful shifted samples.
- The evaluation reports attempted, successful, and failed sample counts.

---

## 6. Optional MLflow Experiment Tracking

StainShift includes optional, manual experiment tracking using MLflow.
Tracking is **disabled by default**, allowing scripts to execute without requiring an MLflow server or local database.
If `--use_mlflow` is explicitly requested but the `mlflow` package is not installed, execution fails immediately with an informative `ImportError`.

### Enabling MLflow Tracking
Pass `--use_mlflow` when executing training, evaluation, or the master experiment runner:
```bash
# Recommended: Local SQLite database store with explicit artifact directory
python run_experiments.py --use_mlflow \
    --mlflow_tracking_uri sqlite:///mlflow.db \
    --mlflow_artifact_root ./mlflow_artifacts \
    --mlflow_experiment_name stainshift_benchmark \
    --run_type smoke_test
```

### CLI Tracking Arguments
- `--use_mlflow`: Enables manual tracking. Fails loudly if `mlflow` is unavailable.
- `--mlflow_tracking_uri`: Relational backend store URI (e.g. `sqlite:///mlflow.db` or environment variable `MLFLOW_TRACKING_URI`). Stores run metadata, parameters, tags, and scalar metrics.
- `--mlflow_artifact_root`: Artifact storage directory (e.g. `./mlflow_artifacts` or environment variable `MLFLOW_ARTIFACT_ROOT`). Stores evaluation summaries, classification reports, plots, and optional checkpoints.
- `--mlflow_experiment_name`: Experiment name in MLflow (default: `stainshift_benchmark`).
- `--run_type`: Explicit tag: `smoke_test` or `full_experiment`. **Important:** This flag only labels the run in MLflow; it does NOT automatically limit epochs or dataset samples. For bounded execution, combine with `--epochs` and `--max_samples_per_class`.
- `--log_models_to_mlflow`: Optional flag to log `.pth` checkpoint weights (disabled by default to prevent storage bloat).

> [!WARNING]
> **Artifact Storage Distinction:** Relocating or copying `mlflow.db` **does not** relocate or copy your artifacts! The SQLite database stores only run metadata, metric series, and parameters. Artifact files (confusion matrices, `eval_results.json`, classification reports) reside in `--mlflow_artifact_root` (or `./mlruns`). You must preserve and copy both.

### Viewing Experiment Runs in MLflow UI
Launch the interactive web UI:
```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlflow_artifacts
```
Then navigate in your browser to `http://127.0.0.1:5000`.

### Persistence & Safe Backup in Google Colab
By default, files saved on the Google Colab ephemeral disk (`/content`) are lost when the instance disconnects.
Because active SQLite database connections can be corrupted if copied while open, follow this safe backup-and-restore procedure:

#### Step 1: Mount Google Drive
```python
from google.colab import drive
drive.mount('/content/drive')
```

#### Step 2: Run Bounded Experiment Locally on High-Speed Ephemeral Disk
Run training on `/content` for fast local I/O:
```bash
python run_experiments.py \
    --data_dir /content/CRC-VAL-HE-7K \
    --epochs 1 --max_samples_per_class 10 --batch_size 16 \
    --use_mlflow \
    --mlflow_tracking_uri "sqlite:////content/mlflow.db" \
    --mlflow_artifact_root "/content/mlflow_artifacts" \
    --run_type smoke_test
```

#### Step 3: Backup Metadata & Artifacts to Google Drive (Safely Closed)
Ensure the Python script has finished executing (closing all SQLite transactions and database handles):
```bash
mkdir -p /content/drive/MyDrive/stainshift_backup
# 1. Backup relational metadata store
cp /content/mlflow.db /content/drive/MyDrive/stainshift_backup/mlflow.db
# 2. Backup artifacts directory
cp -r /content/mlflow_artifacts /content/drive/MyDrive/stainshift_backup/mlflow_artifacts
```

#### Step 4: Restore in a Future Colab Session
To resume or inspect previous runs in a fresh Colab session:
```bash
# Copy persisted files back to local /content
cp /content/drive/MyDrive/stainshift_backup/mlflow.db /content/mlflow.db
cp -r /content/drive/MyDrive/stainshift_backup/mlflow_artifacts /content/mlflow_artifacts

# Launch the MLflow UI pointing to both stores
mlflow ui --backend-store-uri sqlite:////content/mlflow.db --default-artifact-root /content/mlflow_artifacts &
```

---

## 7. Interactive Visualizer (Dashboard)

Launch the dashboard locally:
```bash
streamlit run app.py
```

### Dashboard Features
- **Strict Model Safety:** Inference is disabled if valid trained model checkpoints are missing; random weights are never used.
- **Exact Neutral Controls:** Custom sliders set to neutral $(\alpha_H=1.0, \alpha_E=1.0, \theta=0.0)$ return the exact input image.
- **Honest Outcome Matrix:** For labelled images, predictions are classified into 4 transitions:
  - `Correct ➔ Correct`: Accuracy preserved.
  - `Correct ➔ Incorrect`: Stain-induced misclassification.
  - `Incorrect ➔ Correct`: Spurious correction.
  - `Incorrect ➔ Incorrect`: Persistent misclassification.
- **Unlabelled Uploads:** Disables correctness assertions when ground-truth labels are unavailable.
