"""
StainShift Interactive Dashboard: Visualizing Histopathology Stain Domain Shift
Allows real-time exploration of synthetic Hematoxylin and Eosin perturbations and model behavior.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Tuple

import altair as alt
import numpy as np
import pandas as pd
from PIL import Image
import streamlit as st
import torch
import torch.nn.functional as F

# Ensure repo root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.dataset import IMAGENET_MEAN, IMAGENET_STD
from src.models import (
    CLASS_DESCRIPTIONS,
    CLASS_NAMES,
    load_checkpoint,
)
from src.stain_shift import (
    STAIN_PROFILES,
    DegenerateTissueError,
    InsufficientTissueError,
    MacenkoStainDecomposer,
    StainDecompositionError,
    apply_stain_profile,
)

logger = logging.getLogger(__name__)

st.set_page_config(page_title="StainShift Dashboard", page_icon="🔬", layout="wide")


@st.cache_resource
def discover_and_load_models() -> Dict[str, Dict[str, Any]]:
    """
    Safely discovers and loads valid model checkpoints in the 'models/' directory.
    Never returns uninitialized random weights on missing checkpoints.
    """
    models_dir = BASE_DIR / "models"
    available: Dict[str, Dict[str, Any]] = {}

    candidate_files = [
        ("Baseline (Standard Augmentation)", models_dir / "baseline.pth"),
        ("Stain-Robust (OD Augmentation)", models_dir / "robust_stain_aug.pth"),
        ("100K-NONORM Multi-Center Model", models_dir / "model_100k_nonorm.pth"),
    ]

    # Also search for any other .pth files in models_dir
    if models_dir.is_dir():
        for f in sorted(models_dir.glob("*.pth")):
            label = f.stem.replace("_", " ").title()
            if not any(f.resolve() == path.resolve() for _, path in candidate_files):
                candidate_files.append((f"{label} ({f.name})", f))

    for display_name, ckpt_path in candidate_files:
        if ckpt_path.is_file():
            try:
                model, meta = load_checkpoint(
                    ckpt_path,
                    expected_arch=meta.get("architecture", "mobilenet_v3_small") if 'meta' in locals() and isinstance(meta, dict) else "mobilenet_v3_small",
                    device="cpu",
                    allow_legacy=True,
                )
                available[display_name] = {
                    "model": model,
                    "metadata": meta,
                    "path": ckpt_path,
                }
            except Exception as err:
                logger.warning("Failed to load checkpoint at %s: %s", ckpt_path, err)

    return available


def preprocess_tensor(img_rgb: np.ndarray) -> torch.Tensor:
    """Standard ImageNet normalization matching training pipelines."""
    img_t = torch.from_numpy(img_rgb.transpose((2, 0, 1))).float() / 255.0
    for c in range(3):
        img_t[c] = (img_t[c] - IMAGENET_MEAN[c]) / IMAGENET_STD[c]
    return img_t.unsqueeze(0)


def predict(model: torch.nn.Module, img_rgb: np.ndarray) -> Tuple[int, np.ndarray]:
    """Computes model class probability scores (softmax output)."""
    tensor = preprocess_tensor(img_rgb)
    with torch.no_grad():
        logits = model(tensor)
        probs = F.softmax(logits, dim=1).squeeze(0).numpy()
    pred_idx = int(np.argmax(probs))
    return pred_idx, probs


def render_app() -> None:
    """Renders the interactive Streamlit dashboard."""
    st.title("🔬 StainShift: Histopathology Stain Domain Shift Explorer")
    st.markdown(
        "**Investigating model behavior under synthetic H&E stain perturbations.** "
        "Explore how changes in dye absorption (Beer-Lambert optical density scaling) influence patch classification."
    )
    st.caption(
        "⚠️ **Research Tool Only:** Softmax probabilities reflect raw model output scores and do not represent calibrated clinical confidence or diagnostic certainty."
    )

    models_map = discover_and_load_models()

    # --- Sidebar: Checkpoint Selection ---
    st.sidebar.header("1. Model Checkpoint")
    if not models_map:
        st.sidebar.error("❌ No valid model checkpoints found in `models/`.")
        st.error(
            "### No Checkpoint Available\n"
            "Inference is disabled because no trained checkpoints were found in the `models/` directory.\n\n"
            "To run inference, please train a model using `python run_experiments.py` or place a valid `.pth` checkpoint in `models/`."
        )
        st.stop()

    selected_model_name = st.sidebar.selectbox("Active Model", list(models_map.keys()))
    active_entry = models_map[selected_model_name]
    active_model = active_entry["model"]
    active_meta = active_entry["metadata"]

    with st.sidebar.expander("Model Provenance & Metadata", expanded=False):
        st.write(f"**Path:** `{active_entry['path'].name}`")
        st.write(f"**Provenance:** `{active_meta.get('provenance', 'unknown')}`")
        st.write(f"**Architecture:** `{active_meta.get('architecture', 'mobilenet_v3_small')}`")
        if "epoch" in active_meta:
            st.write(f"**Epoch:** {active_meta['epoch']}")
        if "val_f1" in active_meta and active_meta["val_f1"] is not None:
            st.write(f"**Val F1:** {active_meta['val_f1']:.4f}")
        if "warning" in active_meta:
            st.warning(active_meta["warning"])

    # --- Sidebar: Patch Selection ---
    st.sidebar.header("2. Histopathology Patch")
    data_dir = BASE_DIR / "data" / "CRC-VAL-HE-7K-png"
    patch_source = st.sidebar.radio("Patch Source", ["Dataset Directory", "Upload Custom Image"])

    selected_file: Optional[Path] = None
    ground_truth_class: Optional[str] = None
    original_img: Optional[Image.Image] = None

    if patch_source == "Dataset Directory":
        if not data_dir.is_dir():
            st.sidebar.warning(f"Dataset directory not found at `{data_dir}`.")
            st.info("Upload an image patch or extract CRC-VAL-HE-7K into `data/CRC-VAL-HE-7K-png/`.")
            st.stop()

        selected_class = st.sidebar.selectbox("Filter by True Tissue Class", CLASS_NAMES, index=8)  # TUM default
        class_files = sorted(data_dir.glob(f"{selected_class}-*.png"))

        if not class_files:
            st.sidebar.warning(f"No patches found for class `{selected_class}` in `{data_dir}`.")
            st.stop()

        selected_file = st.sidebar.selectbox(
            "Choose Patch",
            class_files,
            format_func=lambda x: x.name
        )
        ground_truth_class = selected_class
        original_img = Image.open(selected_file).convert("RGB")
        st.sidebar.info(f"**Known Label:** `{ground_truth_class}` — {CLASS_DESCRIPTIONS.get(ground_truth_class, '')}")

    else:
        uploaded = st.sidebar.file_uploader("Upload Patch (PNG/JPG)", type=["png", "jpg", "jpeg"])
        if uploaded is None:
            st.info("Please upload an H&E histopathology patch image to explore.")
            st.stop()
        original_img = Image.open(uploaded).convert("RGB")
        ground_truth_class = None
        st.sidebar.caption("Unlabelled upload: Ground-truth correctness cannot be computed.")

    # --- Sidebar: Stain Controls ---
    st.sidebar.header("3. Stain Perturbation Engine")
    profile_choice = st.sidebar.selectbox(
        "Stain Profile / Control",
        ["Custom Controls", "Reconstruction Control (Macenko)"] + list(STAIN_PROFILES.keys())
    )

    is_neutral_custom = False
    is_reconstruction_only = False

    if profile_choice == "Custom Controls":
        alpha_h = st.sidebar.slider("Hematoxylin Intensity (α_H)", 0.40, 2.00, 1.00, 0.05)
        alpha_e = st.sidebar.slider("Eosin Intensity (α_E)", 0.40, 2.00, 1.00, 0.05)
        rot_deg = st.sidebar.slider("Stain Vector Rotation (°)", -15.0, 15.0, 0.0, 0.5)
        is_neutral_custom = (abs(alpha_h - 1.0) < 1e-4 and abs(alpha_e - 1.0) < 1e-4 and abs(rot_deg) < 1e-4)
        if is_neutral_custom:
            st.sidebar.caption("ℹ️ Neutral settings selected: exact original pixels bypassed.")
    elif profile_choice == "Reconstruction Control (Macenko)":
        is_reconstruction_only = True
        alpha_h = 1.0
        alpha_e = 1.0
        rot_deg = 0.0
        st.sidebar.caption("ℹ️ Tests deconvolution/reconstruction artifacts without stain perturbation.")
    else:
        cfg = STAIN_PROFILES[profile_choice]
        alpha_h = cfg["alpha_h"]
        alpha_e = cfg["alpha_e"]
        rot_deg = cfg["stain_rot_deg"]
        st.sidebar.markdown(f"**Description:**\n*{cfg['description']}*")

    # --- Image Transformation ---
    orig_np = np.array(original_img)
    decomposer = MacenkoStainDecomposer()

    transform_status = "SUCCESS"
    transform_error: Optional[str] = None
    shifted_np: np.ndarray

    if profile_choice == "original" or is_neutral_custom:
        # Exact pixel copy contract
        shifted_np = orig_np.copy()
        transform_status = "EXACT_NEUTRAL"
    elif is_reconstruction_only or profile_choice == "reconstruction_only":
        try:
            shifted_np = decomposer.reconstruct(orig_np)
            transform_status = "RECONSTRUCTION_ONLY"
        except (StainDecompositionError, InsufficientTissueError, DegenerateTissueError, ValueError) as err:
            transform_status = "FAILED"
            transform_error = str(err)
            shifted_np = orig_np.copy()
    else:
        try:
            shifted_np = decomposer.perturb(orig_np, alpha_h=alpha_h, alpha_e=alpha_e, stain_rot_deg=rot_deg)
        except (StainDecompositionError, InsufficientTissueError, DegenerateTissueError, ValueError) as err:
            transform_status = "FAILED"
            transform_error = str(err)
            shifted_np = orig_np.copy()

    # Run Predictions
    orig_pred_idx, orig_probs = predict(active_model, orig_np)
    shift_pred_idx, shift_probs = predict(active_model, shifted_np)

    orig_pred_name = CLASS_NAMES[orig_pred_idx]
    shift_pred_name = CLASS_NAMES[shift_pred_idx]

    # --- Display Side-by-Side ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Original Patch")
        st.image(original_img, use_container_width=True)
        if ground_truth_class:
            orig_is_correct = (orig_pred_name == ground_truth_class)
            status_label = "✅ Correct" if orig_is_correct else "❌ Incorrect"
            st.markdown(
                f"**Model Top Prediction:** `{orig_pred_name}` ({orig_probs[orig_pred_idx]*100:.1f}%) — {status_label}\n\n"
                f"**Ground Truth:** `{ground_truth_class}`"
            )
        else:
            orig_is_correct = None
            st.markdown(f"**Model Top Prediction:** `{orig_pred_name}` ({orig_probs[orig_pred_idx]*100:.1f}%)")

    with col2:
        st.subheader(f"Shifted Condition ({profile_choice})")
        st.image(shifted_np, use_container_width=True)

        if transform_status == "FAILED":
            st.error(f"❌ **Transformation Failed:** {transform_error}. Comparison marked INVALID.")
            st.caption("Display shows unmodified fallback; predictions are not valid for this condition.")
        elif transform_status == "EXACT_NEUTRAL":
            st.info("ℹ️ Exact original pixels preserved (neutral parameter bypass).")
        elif transform_status == "RECONSTRUCTION_ONLY":
            st.caption("ℹ️ Macenko reconstruction control (unperturbed optical density).")

        if ground_truth_class and transform_status != "FAILED":
            shift_is_correct = (shift_pred_name == ground_truth_class)
            shift_status_label = "✅ Correct" if shift_is_correct else "❌ Incorrect"
            st.markdown(
                f"**Model Top Prediction:** `{shift_pred_name}` ({shift_probs[shift_pred_idx]*100:.1f}%) — {shift_status_label}\n\n"
                f"**Ground Truth:** `{ground_truth_class}`"
            )
        elif transform_status != "FAILED":
            shift_is_correct = None
            st.markdown(f"**Model Top Prediction:** `{shift_pred_name}` ({shift_probs[shift_pred_idx]*100:.1f}%)")

    # --- Outcome Categorization ---
    if transform_status != "FAILED":
        st.markdown("---")
        st.subheader("Transition Analysis")

        pred_changed = (orig_pred_name != shift_pred_name)
        change_text = f"Predicted class changed from **{orig_pred_name}** to **{shift_pred_name}**." if pred_changed else f"Predicted class remained **{shift_pred_name}**."

        if ground_truth_class:
            # 4-way transition matrix
            if orig_is_correct and shift_is_correct:
                transition = "Correct ➔ Correct (Accuracy Preserved)"
                st.success(f"**Outcome:** `{transition}`. {change_text}")
            elif orig_is_correct and not shift_is_correct:
                transition = "Correct ➔ Incorrect (Stain-Induced Misclassification)"
                st.error(f"**Outcome:** `{transition}`. {change_text}")
            elif not orig_is_correct and shift_is_correct:
                transition = "Incorrect ➔ Correct (Spurious Correction)"
                st.warning(f"**Outcome:** `{transition}`. {change_text}")
            else:
                transition = "Incorrect ➔ Incorrect (Persistent Error)"
                st.info(f"**Outcome:** `{transition}`. {change_text}")
        else:
            # Unlabelled
            if pred_changed:
                st.warning(f"**Prediction Shift:** {change_text} (Ground truth unknown).")
            else:
                st.info(f"**Prediction Stable:** {change_text} (Ground truth unknown).")

    # --- Class Probability Scores ---
    st.subheader("Model Class Probability Scores")
    chart_data = []
    for i, cname in enumerate(CLASS_NAMES):
        chart_data.append({"Class": cname, "Score": float(orig_probs[i]), "Condition": "Original"})
        chart_data.append({"Class": cname, "Score": float(shift_probs[i]), "Condition": "Shifted"})

    df_chart = pd.DataFrame(chart_data)
    chart = (
        alt.Chart(df_chart)
        .mark_bar()
        .encode(
            x=alt.X("Class:N", title="Tissue Class"),
            y=alt.Y("Score:Q", title="Model Probability Score", scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("Condition:N", scale=alt.Scale(domain=["Original", "Shifted"], range=["#1f77b4", "#e377c2"])),
            xOffset="Condition:N"
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)


if __name__ == "__main__":
    render_app()
