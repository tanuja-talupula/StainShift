# StainShift Audit and Scientific Corrections Log

This document records the verification, repairs, and test coverage performed on StainShift starting from commit `49d1ea3b8a769aa932d5e819239d13bbb7e71cc4`.

---

## 1. Verified Findings & Repairs

### 1. Augmentation Mode Mismatch & Silent Fallback
- **Confirmed Location:** `src/dataset.py:35, 66–85`
- **Issue:** In the original repository, `CRCDataset.__init__` checked `if transform_mode == "stain_augmented"` to initialize `self.decomposer`. However, the training script and dataset `__getitem__` checked `self.transform_mode == "train_stain_augmented"`. When running augmented training, `self.decomposer` was `None`. When `self.decomposer.perturb(...)` was called on line 83, Python raised an `AttributeError`, which was caught and swallowed by `except Exception: pass`. As a result, the intended stain perturbation failed for all training samples in this path, falling back to the unperturbed (geometric-only) image while training proceeded.
- **Correction:**
  - Standardized transform mode names: supported modes include `train_stain_augmented`, `train_standard`, `eval_standard`, `eval_shifted`, and `eval_reconstruction` (with backward compatibility aliases).
  - Ensured `self.decomposer` is properly initialized whenever stain augmentation, shift evaluation, or reconstruction controls are active.
  - Removed broad `except Exception: pass` swallows. Unexpected programming errors fail loudly.
  - Specific anticipated numerical errors (`StainDecompositionError`, `InsufficientTissueError`, `DegenerateTissueError`) are caught, counted, and recorded with file path and failure reason.
- **Evidence / Tests:** `tests/test_dataset.py::test_decomposer_initialized_for_train_stain_augmented`, `test_train_stain_augmented_invokes_perturbation`, and `test_unexpected_programming_errors_fail_loudly_when_fail_mode_raise`.

---

### 2. Silent Random Model Weights Fallback
- **Confirmed Location:** `app.py:35–56`
- **Issue:** When `.pth` checkpoints were missing, `get_model("mobilenet_v3_small", pretrained=False)` instantiated uninitialized random weights, which were used for inference without notifying the user.
- **Correction:**
  - Implemented `discover_and_load_models()` in `app.py` and `load_checkpoint()` in `src/models.py`.
  - Missing or invalid checkpoints display clear UI alerts and disable inference entirely.
  - Model selection in the dashboard lists only verified, genuinely available checkpoints.
- **Evidence / Tests:** `tests/test_models.py::test_load_checkpoint_missing_file_raises_filenotfound` and `tests/test_dashboard_logic.py::test_discover_and_load_models_ignores_empty`.

---

### 3. Hardcoded Windows Paths and Import Side-Effects
- **Confirmed Location:** `src/models.py:12–14`, `run_experiments.py:14–16`, `train_100k_val_7k.py:20–22`, `src/train.py:148–150`, `src/evaluate.py:131–133`
- **Issue:** Hardcoded Windows paths (`C:\Users\HP\.gemini\...`) caused import-time filesystem writes (`os.makedirs`) and broke execution on non-Windows operating systems.
- **Correction:**
  - Removed all hardcoded absolute Windows paths.
  - Used `pathlib.Path` with project-relative defaults, CLI flags, and documented configuration arguments.
  - Eliminated import-time side-effects: importing `src.models`, `src.dataset`, or other modules does not create directories or mutate environment variables.
- **Evidence / Tests:** `tests/test_models.py::test_no_import_side_effects` and `tests/test_cli.py`.

---

### 4. Lossy Deconvolution on Neutral Parameters and Conflated Outcomes
- **Confirmed Location:** `src/stain_shift.py:93–131`, `app.py:173–183`
- **Issue:** Neutral settings ($\alpha_H=1.0, \alpha_E=1.0, \theta=0.0$) previously ran through deconvolution and reconstruction, introducing lossy optical density discretization errors. In `app.py`, any class flip was labelled an error, any unchanged prediction was called robust, and confidence drops were treated as model failures.
- **Correction:**
  - Added exact identity bypass for neutral controls: `alpha_h=1.0, alpha_e=1.0, rot=0.0` preserves exact original pixels (`np.array_equal == True`).
  - Isolated `reconstruction_only` as a distinct named benchmark control to separate deconvolution artifacts from stain shift effects.
  - Replaced misleading dashboard outcome messages with a 4-way transition matrix for labelled images:
    `Correct ➔ Correct`, `Correct ➔ Incorrect`, `Incorrect ➔ Correct`, `Incorrect ➔ Incorrect`.
  - Softmax probabilities are explicitly identified as uncalibrated model scores.
- **Evidence / Tests:** `tests/test_stain_shift.py::test_original_profile_exact_pixel_equality`, `test_neutral_custom_parameters_exact_pixel_equality`, and `test_reconstruction_only_is_distinct_from_original`.

---

### 5. Checkpoint Metadata Provenance & Stale Checkpoint Reuse
- **Confirmed Location:** `run_experiments.py:38–56`, `src/models.py`
- **Issue:** Existing checkpoints were unconditionally reused without verifying architecture, training mode, seed, or class mapping compatibility.
- **Correction:**
  - Introduced `save_checkpoint` with rich metadata headers: `format_version`, `provenance`, `architecture`, `class_names`, `class_to_idx`, `metrics`, `train_mode`, `seed`, and `split_info`.
  - In `run_experiments.py`, unconditional reuse was replaced with an explicit `--checkpoint_policy` (`train_new`, `reuse_if_valid`, `eval_only`).
  - Added `--dry-run` CLI options across all execution scripts to validate configuration without launching expensive jobs.
- **Evidence / Tests:** `tests/test_models.py::test_save_and_load_checkpoint_roundtrip`, `test_load_checkpoint_architecture_mismatch_raises_valueerror`, `test_legacy_checkpoint_loading_policy`, and `tests/test_cli.py`.

---

### 6. Model Selection Protocol & RNG Reseeding
- **Confirmed Location:** `train_100k_val_7k.py:54, 191–218`
- **Issue:** In `train_100k_val_7k.py`, `np.random.seed(42)` was re-seeded on every iteration of the class loop, producing identical sampling indices across classes of equal size. Checkpoints were selected directly using validation F1 on CRC-VAL-HE-7K while simultaneously presenting that validation run as untouched external test performance.
- **Correction:**
  - Replaced per-loop reseeding with an isolated `np.random.default_rng(seed)` instance.
  - Explicitly separated checkpoint selection from untouched external evaluation via `--selection_protocol`: when 7K is used for model selection, output reports and saved checkpoints are explicitly labelled as `"checkpoint_selection_protocol": "external_val_cohort_used_for_selection"`, noting that 7K cannot be claimed as an untouched final test.
- **Evidence / Tests:** Code audit and `train_100k_val_7k.py` argument validation.

---

### 7. Reinhard Color Normalizer Numerical Scaling
- **Confirmed Location:** `src/stain_shift.py:155–165`
- **Issue:** The default target mean was set to `[2.95, 0.12, -0.05]`. In Ruderman log10 LMS color space, normalized RGB values in $[0, 1]$ have negative log values, so the true L channel mean for H&E tissue is approximately $-0.40$. Setting target L mean to $+2.95$ caused `10^(lab * LAB_TO_LMS)` to blow up to $>10,000$, resulting in 100% saturation at 255 for all pixels.
- **Correction:**
  - Added `fit(reference_img)` to empirically compute target statistics from reference H&E images in the identical color space.
  - Calibrated default target statistics to `[-0.40, -0.06, 0.02]` matching digital H&E tissue in log10 Ruderman space.
  - Added saturation checks and finite output verification.
- **Evidence / Tests:** `tests/test_stain_shift.py::test_reinhard_calibrated_transfer_no_blowout` and `test_reinhard_fit_on_reference`.

---

### 8. Reproducible Splits and Determinism
- **Confirmed Location:** `src/dataset.py:119–158`
- **Issue:** `os.listdir` has arbitrary filesystem-dependent ordering, and split caching stored absolute paths.
- **Correction:**
  - File paths are sorted (`sorted(glob)`) prior to seeded shuffling.
  - Sample disjointness between train, val, and test splits is strictly verified (`set & set == empty`).
  - Cache files store dataset-relative paths for portability.
- **Evidence / Tests:** `tests/test_splits.py::test_splits_determinism_and_reproducibility` and `test_splits_sample_disjointness`.

---

## 2. Status of Existing Historical Results

The existing JSON files in `experiments/`:
- `baseline_stress_test.json`
- `robust_stress_test.json`
- `comparison_summary.json`
- `model_100k_nonorm_results.json`

**Are unverified historical artifacts.** Because the previous training code failed to perturb images during augmented training, previous "robust" models were effectively trained on geometric augmentations only. To obtain valid, scientifically reproducible results, fresh training runs must be executed using the repaired pipeline.

---

## 3. Remaining Limitations
1. **Biological and Physical Fidelity:** Synthetic OD modifications simulate dye concentration changes, but do not reproduce multi-center variation in tissue fixation, microtome slice thickness artifacts, illumination spectra, or scanner-specific sensor color response functions.
2. **Slide-Level Grouping:** When patient or slide identifiers are absent from dataset filenames, splitting is performed at the patch level. While patch disjointness is strictly enforced, patient-level generalization requires slide-level grouping metadata.
3. **Hardware / Compute:** No training on the full 100K or 7K datasets was initiated during this engineering repair phase, adhering to the non-negotiable rule prohibiting unauthorized expensive training runs.
