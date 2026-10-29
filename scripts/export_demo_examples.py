"""
Demo Option B Exporter for StainShift.
Extracts the first sorted held-out test patch per class, applies the 8 distinct
stain profiles, evaluates through Stage A checkpoints, and exports lossless PNG
patches with verified model probability distributions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Dict, List

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F

from src.dataset import IMAGENET_MEAN, IMAGENET_STD
from src.models import CLASS_NAMES, CLASS_DESCRIPTIONS, load_checkpoint
from src.stain_shift import DISTINCT_STAIN_PROFILES, apply_stain_profile


def compute_sha256(filepath: Path) -> str:
    """Computes SHA-256 hash of a file."""
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def export_demo_examples(
    data_dir: str = "data/CRC-VAL-HE-7K",
    splits_cache: str = "data/CRC-VAL-HE-7K/splits.json",
    models_dir: str = "models/full_benchmark_20261029_1838",
    output_dir: str = "website/public/demo",
    mlflow_run_id: str = "c76c59f4bd7c4fe39f2ed2135856845a",
) -> Dict[str, Any]:
    """Generates verified demonstration patches and manifest."""
    data_p = Path(data_dir)
    splits_p = Path(splits_cache)
    models_p = Path(models_dir)
    out_p = Path(output_dir)
    images_dir = out_p / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    baseline_ckpt = models_p / "baseline.pth"
    robust_ckpt = models_p / "robust_stain_aug.pth"
    split_manifest_p = data_p / "frozen_final_split_manifest.json"

    if not baseline_ckpt.is_file():
        raise FileNotFoundError(f"Baseline checkpoint not found: {baseline_ckpt}")
    if not robust_ckpt.is_file():
        raise FileNotFoundError(f"Robust checkpoint not found: {robust_ckpt}")
    if not split_manifest_p.is_file():
        raise FileNotFoundError(f"Split manifest not found: {split_manifest_p}")

    baseline_sha = compute_sha256(baseline_ckpt)
    robust_sha = compute_sha256(robust_ckpt)
    split_manifest_sha = compute_sha256(split_manifest_p)

    # Load Stage A models
    device = "cpu"
    baseline_model, _ = load_checkpoint(baseline_ckpt, expected_arch="mobilenet_v3_small", expected_classes=CLASS_NAMES, device=device)
    robust_model, _ = load_checkpoint(robust_ckpt, expected_arch="mobilenet_v3_small", expected_classes=CLASS_NAMES, device=device)
    baseline_model.eval()
    robust_model.eval()

    # Load frozen splits
    with open(splits_p, "r", encoding="utf-8") as f:
        splits = json.load(f)

    test_files = splits["test"]["files"]
    test_labels = splits["test"]["labels"]

    # Select the first lexicographically sorted patch per class
    selection_rule = "First lexicographically sorted patch ID per class in the frozen held-out test split (splits.json)"
    selected_patches: List[Dict[str, Any]] = []

    for cidx, cname in enumerate(CLASS_NAMES):
        class_files = sorted([f for f, l in zip(test_files, test_labels) if l == cidx])
        if not class_files:
            raise ValueError(f"No test files found for class {cname}")
        rel_path = class_files[0]
        full_path = data_p / rel_path
        patch_id = Path(rel_path).stem
        selected_patches.append({
            "class_idx": cidx,
            "class_name": cname,
            "rel_path": rel_path,
            "full_path": full_path,
            "patch_id": patch_id,
        })

    mean = np.array(IMAGENET_MEAN, dtype=np.float32).reshape(1, 1, 3)
    std = np.array(IMAGENET_STD, dtype=np.float32).reshape(1, 1, 3)

    manifest_examples: List[Dict[str, Any]] = []
    total_images_saved = 0
    total_image_bytes = 0

    with torch.no_grad():
        for item in selected_patches:
            cidx = item["class_idx"]
            cname = item["class_name"]
            patch_id = item["patch_id"]
            full_p = item["full_path"]

            # Load 8-bit RGB image
            with Image.open(full_p) as pil_img:
                raw_rgb = np.array(pil_img.convert("RGB"), dtype=np.uint8)

            assert raw_rgb.shape == (224, 224, 3), f"Unexpected shape {raw_rgb.shape} for {patch_id}"

            example_entry: Dict[str, Any] = {
                "patch_id": patch_id,
                "tissue_class": cname,
                "tissue_class_description": CLASS_DESCRIPTIONS.get(cname, cname),
                "source_relative_path": item["rel_path"],
                "conditions": {},
            }

            for cond in DISTINCT_STAIN_PROFILES:
                # Apply deterministic transformation
                transformed_rgb = apply_stain_profile(raw_rgb, profile_name=cond)

                # Save lossless PNG
                out_filename = f"{patch_id}_{cond}.png"
                out_image_path = images_dir / out_filename
                Image.fromarray(transformed_rgb).save(out_image_path, format="PNG", optimize=True)

                total_images_saved += 1
                total_image_bytes += out_image_path.stat().st_size

                # Preprocess for model: normalize and convert to tensor
                norm_img = ((transformed_rgb.astype(np.float32) / 255.0) - mean) / std
                tensor_img = torch.from_numpy(norm_img.transpose(2, 0, 1)).unsqueeze(0).to(torch.float32)

                # Inference on Baseline Model
                b_logits = baseline_model(tensor_img)
                b_probs = F.softmax(b_logits, dim=1).squeeze(0).numpy()
                b_pred_idx = int(np.argmax(b_probs))
                b_conf = float(b_probs[b_pred_idx])
                b_correct = (b_pred_idx == cidx)

                # Inference on Robust Model
                r_logits = robust_model(tensor_img)
                r_probs = F.softmax(r_logits, dim=1).squeeze(0).numpy()
                r_pred_idx = int(np.argmax(r_probs))
                r_conf = float(r_probs[r_pred_idx])
                r_correct = (r_pred_idx == cidx)

                # Verification assertions
                assert math.isclose(float(np.sum(b_probs)), 1.0, rel_tol=1e-4), "Baseline probabilities do not sum to 1"
                assert math.isclose(float(np.sum(r_probs)), 1.0, rel_tol=1e-4), "Robust probabilities do not sum to 1"
                assert b_conf == float(b_probs[b_pred_idx]), "Confidence mismatch"
                assert r_conf == float(r_probs[r_pred_idx]), "Confidence mismatch"

                b_prob_dict = {CLASS_NAMES[i]: round(float(b_probs[i]), 4) for i in range(len(CLASS_NAMES))}
                r_prob_dict = {CLASS_NAMES[i]: round(float(r_probs[i]), 4) for i in range(len(CLASS_NAMES))}

                example_entry["conditions"][cond] = {
                    "image_url": f"/demo/images/{out_filename}",
                    "baseline": {
                        "predicted_class": CLASS_NAMES[b_pred_idx],
                        "predicted_class_description": CLASS_DESCRIPTIONS.get(CLASS_NAMES[b_pred_idx], CLASS_NAMES[b_pred_idx]),
                        "confidence": round(b_conf, 4),
                        "is_correct": b_correct,
                        "probabilities": b_prob_dict,
                    },
                    "robust_stain_aug": {
                        "predicted_class": CLASS_NAMES[r_pred_idx],
                        "predicted_class_description": CLASS_DESCRIPTIONS.get(CLASS_NAMES[r_pred_idx], CLASS_NAMES[r_pred_idx]),
                        "confidence": round(r_conf, 4),
                        "is_correct": r_correct,
                        "probabilities": r_prob_dict,
                    },
                }

            manifest_examples.append(example_entry)

    demo_manifest: Dict[str, Any] = {
        "metadata": {
            "title": "StainShift Verified Precomputed Demonstration Examples",
            "selection_rule": selection_rule,
            "disclaimer": "Precomputed verified actual model outputs on the first lexicographically sorted held-out test patches per class. Deterministic selection does not imply an unbiased or representative sample. Zero synthetic logits or browser-side approximations.",
            "mlflow_evaluation_run_id": mlflow_run_id,
            "frozen_split_manifest_sha256": split_manifest_sha,
            "checkpoints": {
                "baseline": {
                    "path": str(baseline_ckpt),
                    "sha256": baseline_sha,
                    "architecture": "mobilenet_v3_small",
                },
                "robust_stain_aug": {
                    "path": str(robust_ckpt),
                    "sha256": robust_sha,
                    "architecture": "mobilenet_v3_small",
                },
            },
            "preprocessing": {
                "resize": [224, 224],
                "mean": IMAGENET_MEAN,
                "std": IMAGENET_STD,
            },
            "total_patches_selected": len(selected_patches),
            "conditions_per_patch": len(DISTINCT_STAIN_PROFILES),
            "total_images_generated": total_images_saved,
            "total_image_bytes": total_image_bytes,
            "image_format": "PNG (lossless RGB, 224x224)",
        },
        "classes": CLASS_NAMES,
        "conditions": DISTINCT_STAIN_PROFILES,
        "examples": manifest_examples,
    }

    manifest_path = out_p / "demo_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(demo_manifest, f, indent=2)

    print(f"Generated {total_images_saved} lossless PNG demo patches ({total_image_bytes / (1024*1024):.2f} MB total).")
    print(f"Demo manifest successfully saved to: {manifest_path}")

    # Also sync a copy to root public/demo for repo-level consistency
    root_public_demo = Path("public/demo")
    root_public_demo.mkdir(parents=True, exist_ok=True)
    with open(root_public_demo / "demo_manifest.json", "w", encoding="utf-8") as f:
        json.dump(demo_manifest, f, indent=2)

    return demo_manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Option B verified demonstration examples")
    parser.add_argument("--data_dir", type=str, default="data/CRC-VAL-HE-7K")
    parser.add_argument("--splits_cache", type=str, default="data/CRC-VAL-HE-7K/splits.json")
    parser.add_argument("--models_dir", type=str, default="models/full_benchmark_20261029_1838")
    parser.add_argument("--output_dir", type=str, default="website/public/demo")
    args = parser.parse_args()

    export_demo_examples(
        data_dir=args.data_dir,
        splits_cache=args.splits_cache,
        models_dir=args.models_dir,
        output_dir=args.output_dir,
    )
