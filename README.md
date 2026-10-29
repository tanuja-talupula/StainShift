# 🔬 StainShift: Histopathology Stain Domain Shift Benchmark

> **Research Question:** *Does the model still work when the stain colour changes?*

This project investigates the domain generalization and shortcut learning behaviors of deep neural networks on histological images when subjected to real-world and synthetic hematoxylin & eosin (H&E) staining shifts.

---

## 1. Dataset: Zenodo 1214456 (`CRC-VAL-HE-7K`)

The dataset is derived from the colorectal cancer benchmark by Jakob Nikolas Kather et al. ([DOI: 10.5281/zenodo.1214456](https://doi.org/10.5281/zenodo.1214456)):
- **Total Images:** 7,180 non-overlapping tissue tiles ($224 \times 224$ px at $0.5$ $\mu\text{m/px}$).
- **Cohorts:** Formally part of the independent DACHS validation cohort (no patient overlap with NCT-CRC-HE-100K).
- **Tissue Classes (9 total):**
  1. `ADI`: Adipose tissue (Fat)
  2. `BACK`: Background (Glass slide)
  3. `DEB`: Debris (Necrotic tissue & preparation artifacts)
  4. `LYM`: Lymphocytes (Immune cell aggregates)
  5. `MUC`: Mucus (Extracellular mucin)
  6. `MUS`: Smooth muscle
  7. `NORM`: Normal colon mucosa
  8. `STR`: Cancer-associated stroma
  9. `TUM`: Colorectal adenocarcinoma epithelium

---

## 2. Theoretical Framework: The Physics of Stain Shift

In transmitted light microscopy, light absorption through dyed tissue follows the **Beer-Lambert Law**:

$$\mathbf{OD} = -\log_{10}\left(\frac{\mathbf{I}}{\mathbf{I}_0}\right) = \mathbf{V} \cdot \mathbf{S}$$

where:
- $\mathbf{I} \in [0, 255]^{H \times W \times 3}$ is the observed transmitted RGB image.
- $\mathbf{OD}$ is the Optical Density matrix.
- $\mathbf{V} \in \mathbb{R}^{HW \times 2}$ represents the spatial concentration of **Hematoxylin** (nuclear basophilic dye) and **Eosin** (cytoplasmic/stromal eosinophilic dye).
- $\mathbf{S} \in \mathbb{R}^{2 \times 3}$ represents the stain matrix in OD space.

### Why standard models fail:
When moving from Hospital A to Hospital B, changes in reagent brand, solution pH, staining duration, slide thickness, and scanner color calibration rotate $\mathbf{S}$ and scale $\mathbf{V}$. Standard CNNs and ViTs rely heavily on low-frequency color distributions as shortcuts, leading to sharp drops in diagnostic accuracy.

---

## 3. Evaluated Stain Shift Regimes

We evaluate models across 7 clinical and synthetic stain variation profiles:

| Profile | $\alpha_H$ (Hematoxylin) | $\alpha_E$ (Eosin) | OD Rotation | Clinical / Scanner Scenario |
| :--- | :---: | :---: | :---: | :--- |
| `original` | 1.00 | 1.00 | $0.0^\circ$ | In-domain baseline reference |
| `heavy_hematoxylin` | 1.65 | 0.85 | $+3.0^\circ$ | Lab A: Hyperchromatic nuclei, thick tissue slice |
| `heavy_eosin` | 0.75 | 1.65 | $-3.0^\circ$ | Lab B: Cytoplasm & desmoplastic stroma over-dominance |
| `pale_understained`| 0.60 | 0.60 | $0.0^\circ$ | Lab C: Rapid destaining, washed out weak contrast |
| `dark_overstained` | 1.50 | 1.50 | $0.0^\circ$ | Lab D: High reagent exposure, heavy global absorption |
| `scanner_warm_shift`| 0.90 | 1.30 | $+8.0^\circ$ | Scanner X (Aperio-like): Warm yellowish-red calibration |
| `scanner_cool_shift`| 1.35 | 0.80 | $-8.0^\circ$ | Scanner Y (Hamamatsu-like): Cool bluish-magenta bias |

---

## 4. Models & Defenses

1. **`model_100k_nonorm` (Multi-Patient Raw H&E Model)**:
   Trained on `NCT-CRC-HE-100K-NONORM` (18,000 class-balanced raw patches from 86 patients) and validated on all 7,180 external patches of `CRC-VAL-HE-7K` (50 patients).
   - In-Domain Training Accuracy: **97.12%**
   - Cross-Cohort Validation Accuracy on 7K: **67.86%** (Macro F1: 0.5931)
   - High tumor sensitivity (**88.56% Recall** for Colorectal Adenocarcinoma Epithelium).
2. **Baseline Model (`baseline.pth`)**:
   Trained on in-domain single-cohort patches with standard geometric augmentation.
3. **Stain-Robust Model (`robust_stain_aug.pth`)**:
   Trained with on-the-fly **Beer-Lambert Optical Density Augmentation** (Macenko decomposition).

---

## 5. Running the Pipeline

### Train & Evaluate:
```bash
python run_experiments.py
```

### Launch Interactive Visualizer:
```bash
streamlit run app.py
```
