"""
StainShift Interactive Dashboard: Visualizing Histopathology Stain Domain Shift
Allows real-time manipulation of Hematoxylin and Eosin concentrations and live inference.
"""

import os
import sys
import glob
import numpy as np
from PIL import Image
import streamlit as st
import torch
import torch.nn.functional as F
import pandas as pd
import altair as alt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ["TORCH_HOME"] = os.path.join(BASE_DIR, "..", "torch_cache")
sys.path.append(BASE_DIR)

from src.models import get_model, CLASS_NAMES, CLASS_DESCRIPTIONS
from src.stain_shift import MacenkoStainDecomposer, STAIN_PROFILES, apply_stain_profile
from src.dataset import IMAGENET_MEAN, IMAGENET_STD

st.set_page_config(page_title="StainShift Dashboard", page_icon="🔬", layout="wide")


@st.cache_resource
def load_models():
    device = torch.device("cpu")
    models_dir = os.path.join(BASE_DIR, "models")

    # Load baseline
    baseline_path = os.path.join(models_dir, "baseline.pth")
    baseline_model = get_model("mobilenet_v3_small", pretrained=False)
    if os.path.exists(baseline_path):
        ckpt = torch.load(baseline_path, map_location=device)
        baseline_model.load_state_dict(ckpt["model_state_dict"])
    baseline_model.eval()

    # Load robust
    robust_path = os.path.join(models_dir, "robust_stain_aug.pth")
    robust_model = get_model("mobilenet_v3_small", pretrained=False)
    if os.path.exists(robust_path):
        ckpt = torch.load(robust_path, map_location=device)
        robust_model.load_state_dict(ckpt["model_state_dict"])
    robust_model.eval()

    # Load 100K-NONORM model
    nonorm_path = os.path.join(models_dir, "model_100k_nonorm.pth")
    nonorm_model = get_model("mobilenet_v3_small", pretrained=False)
    if os.path.exists(nonorm_path):
        ckpt = torch.load(nonorm_path, map_location=device)
        nonorm_model.load_state_dict(ckpt["model_state_dict"])
    nonorm_model.eval()

    return baseline_model, robust_model, nonorm_model


def preprocess_tensor(img_rgb: np.ndarray):
    img = Image.fromarray(img_rgb)
    img_t = torch.from_numpy(np.array(img).transpose((2, 0, 1))).float() / 255.0
    for c in range(3):
        img_t[c] = (img_t[c] - IMAGENET_MEAN[c]) / IMAGENET_STD[c]
    return img_t.unsqueeze(0)


def predict(model, img_rgb: np.ndarray):
    tensor = preprocess_tensor(img_rgb)
    with torch.no_grad():
        logits = model(tensor)
        probs = F.softmax(logits, dim=1).squeeze(0).numpy()
    pred_idx = int(np.argmax(probs))
    return pred_idx, probs


st.title("🔬 StainShift: Histopathology Stain Domain Shift Explorer")
st.markdown(
    "**Does the model still work when the stain colour changes?** "
    "Explore how physical H&E color variation (Beer-Lambert optical density shifts) affects deep learning predictions on colorectal cancer tissue patches."
)

baseline_model, robust_model, nonorm_model = load_models()
decomposer = MacenkoStainDecomposer()

# Sidebar: Select Patch
data_dir = os.path.join(BASE_DIR, "data", "CRC-VAL-HE-7K-png")
st.sidebar.header("1. Select Histopathology Patch")

selected_class = st.sidebar.selectbox("Filter by Tissue Class", CLASS_NAMES, index=8)  # TUM default
class_files = glob.glob(os.path.join(data_dir, f"{selected_class}-*.png"))

if not class_files:
    st.sidebar.warning("No images found in dataset directory. Please ensure dataset is extracted.")
    st.stop()

selected_file = st.sidebar.selectbox(
    "Choose Patch",
    class_files,
    format_func=lambda x: os.path.basename(x)
)

st.sidebar.info(f"**True Label:** `{selected_class}`\n\n*{CLASS_DESCRIPTIONS.get(selected_class, '')}*")

# Sidebar: Stain Shift Controls
st.sidebar.header("2. Stain Perturbation Engine")
profile_choice = st.sidebar.selectbox(
    "Preset Hospital / Scanner Profile",
    ["Custom Controls"] + list(STAIN_PROFILES.keys())
)

if profile_choice == "Custom Controls":
    alpha_h = st.sidebar.slider("Hematoxylin Intensity (α_H)", 0.40, 2.00, 1.00, 0.05)
    alpha_e = st.sidebar.slider("Eosin Intensity (α_E)", 0.40, 2.00, 1.00, 0.05)
    rot_deg = st.sidebar.slider("Optical Density Rotation (°)", -15.0, 15.0, 0.0, 0.5)
else:
    cfg = STAIN_PROFILES[profile_choice]
    alpha_h = cfg["alpha_h"]
    alpha_e = cfg["alpha_e"]
    rot_deg = cfg["stain_rot_deg"]
    st.sidebar.markdown(f"**Profile Description:**\n*{cfg['description']}*")

# Model selection for display
eval_model_type = st.sidebar.radio(
    "Active Model",
    ["100K-NONORM Multi-Patient Model", "Baseline Model (Standard)", "Robust Model (Stain-Augmented)"]
)
if "100K" in eval_model_type:
    active_model = nonorm_model
elif "Baseline" in eval_model_type:
    active_model = baseline_model
else:
    active_model = robust_model

# Load and perturb image
original_img = Image.open(selected_file).convert("RGB")
orig_np = np.array(original_img)

try:
    shifted_np = decomposer.perturb(orig_np, alpha_h=alpha_h, alpha_e=alpha_e, stain_rot_deg=rot_deg)
except Exception as e:
    st.error(f"Decomposition error: {e}")
    shifted_np = orig_np.copy()

# Run Predictions
orig_pred_idx, orig_probs = predict(active_model, orig_np)
shift_pred_idx, shift_probs = predict(active_model, shifted_np)

orig_pred_name = CLASS_NAMES[orig_pred_idx]
shift_pred_name = CLASS_NAMES[shift_pred_idx]

# Display Side-by-Side
col1, col2 = st.columns(2)

with col1:
    st.subheader("Original Patch (In-Domain)")
    st.image(original_img, use_container_width=True)
    orig_correct = orig_pred_name == selected_class
    badge = "✅ Correct" if orig_correct else "❌ Incorrect"
    st.markdown(
        f"**Prediction:** `{orig_pred_name}` ({orig_probs[orig_pred_idx]*100:.1f}%) — {badge}"
    )

with col2:
    st.subheader(f"Shifted Patch ({profile_choice})")
    st.image(shifted_np, use_container_width=True)
    shift_correct = shift_pred_name == selected_class
    badge_shift = "✅ Correct" if shift_correct else "❌ Shift Failure"
    st.markdown(
        f"**Prediction:** `{shift_pred_name}` ({shift_probs[shift_pred_idx]*100:.1f}%) — {badge_shift}"
    )

# Alert callout if prediction flipped
if orig_pred_name != shift_pred_name:
    st.error(
        f"⚠️ **Domain Shift Error Detected!** Changing stain color flipped model classification from **{orig_pred_name}** to **{shift_pred_name}**."
    )
elif shift_probs[shift_pred_idx] < orig_probs[orig_pred_idx] - 0.20:
    st.warning(
        f"⚠️ **Confidence Degradation:** Model maintained prediction **{shift_pred_name}**, but confidence dropped from {orig_probs[orig_pred_idx]*100:.1f}% to {shift_probs[shift_pred_idx]*100:.1f}%."
    )
else:
    st.success("✅ Model remained robust under this stain perturbation.")

# Probability Distribution Chart
st.subheader("Class Probability Comparison")
chart_data = []
for i, cname in enumerate(CLASS_NAMES):
    chart_data.append({"Class": cname, "Probability": float(orig_probs[i]), "Condition": "Original"})
    chart_data.append({"Class": cname, "Probability": float(shift_probs[i]), "Condition": "Shifted"})

df_chart = pd.DataFrame(chart_data)
chart = (
    alt.Chart(df_chart)
    .mark_bar()
    .encode(
        x=alt.X("Class:N", title="Tissue Class"),
        y=alt.Y("Probability:Q", title="Probability", scale=alt.Scale(domain=[0, 1])),
        color=alt.Color("Condition:N", scale=alt.Scale(domain=["Original", "Shifted"], range=["#1f77b4", "#ff7f0e"])),
        xOffset="Condition:N"
    )
    .properties(height=320)
)
st.altair_chart(chart, use_container_width=True)
