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
  ```bash
  python run_experiments.py --dry-run
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

## 6. Interactive Visualizer (Dashboard)

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
