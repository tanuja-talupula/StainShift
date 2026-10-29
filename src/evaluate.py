"""
StainShift: Model Stress-Testing & Robustness Evaluation
Quantifies model performance degradation under physical stain shifts and scanner variations.
"""

import os
import argparse
import json
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from sklearn.metrics import classification_report, accuracy_score, f1_score

from .models import get_model, CLASS_NAMES
from .dataset import CRCDataset, get_data_splits
from .stain_shift import STAIN_PROFILES


@torch.no_grad()
def evaluate_stain_profile(model, file_paths, labels, profile_name: str, batch_size: int = 32, device: str = "cpu"):
    """Evaluates the model on test patches under a specific stain shift profile."""
    dataset = CRCDataset(
        file_paths=file_paths,
        labels=labels,
        transform_mode="eval_shifted",
        stain_profile=profile_name
    )
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    model.eval()
    all_preds = []
    all_targets = []
    all_confs = []

    for images, targets, _ in loader:
        images = images.to(device)
        outputs = model(images)
        probs = F.softmax(outputs, dim=1)
        confs, preds = torch.max(probs, dim=1)

        all_preds.extend(preds.cpu().numpy())
        all_targets.extend(targets.numpy())
        all_confs.extend(confs.cpu().numpy())

    acc = accuracy_score(all_targets, all_preds)
    f1 = f1_score(all_targets, all_preds, average="macro", zero_division=0)
    mean_conf = float(np.mean(all_confs))

    report = classification_report(all_targets, all_preds, target_names=CLASS_NAMES, output_dict=True, zero_division=0)

    return {
        "accuracy": float(acc),
        "macro_f1": float(f1),
        "mean_confidence": mean_conf,
        "classification_report": report
    }


def run_stress_test(
    checkpoint_path: str,
    data_dir: str,
    splits_cache: str,
    output_json: str = None,
    batch_size: int = 32,
    device: str = "cpu"
):
    print(f"=== Stress-Testing Checkpoint: {checkpoint_path} ===")
    device = torch.device(device)

    # Load checkpoint
    ckpt = torch.load(checkpoint_path, map_location=device)
    arch = ckpt.get("arch", "mobilenet_v3_small")
    model = get_model(arch=arch, pretrained=False, num_classes=len(CLASS_NAMES))
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()

    # Get test data
    _, _, test_split = get_data_splits(data_dir, splits_cache)
    file_paths = test_split["files"]
    labels = test_split["labels"]
    print(f"Evaluating across {len(file_paths)} test patches for {len(STAIN_PROFILES)} stain regimes...")

    results = {}
    baseline_acc = None
    baseline_f1 = None

    for profile_name, info in STAIN_PROFILES.items():
        print(f"\nEvaluating Profile: [{profile_name}] - {info['description']}...")
        metrics = evaluate_stain_profile(
            model=model,
            file_paths=file_paths,
            labels=labels,
            profile_name=profile_name,
            batch_size=batch_size,
            device=device
        )

        acc = metrics["accuracy"]
        f1 = metrics["macro_f1"]

        if profile_name == "original":
            baseline_acc = acc
            baseline_f1 = f1
            delta_acc = 0.0
            delta_f1 = 0.0
        else:
            delta_acc = (acc - baseline_acc) * 100.0
            delta_f1 = f1 - baseline_f1

        metrics["delta_acc_pct"] = round(delta_acc, 2)
        metrics["delta_f1"] = round(delta_f1, 4)
        results[profile_name] = metrics

        delta_str = f"({delta_acc:+.2f}%)" if profile_name != "original" else "(Reference)"
        print(f"  -> Accuracy: {acc*100:.2f}% {delta_str} | Macro F1: {f1:.4f} | Conf: {metrics['mean_confidence']:.3f}")

    if output_json:
        os.makedirs(os.path.dirname(output_json), exist_ok=True)
        with open(output_json, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nFull stress test report written to: {output_json}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--data_dir", type=str, default=r"C:\Users\HP\.gemini\antigravity\scratch\stainshift\data\CRC-VAL-HE-7K-png")
    parser.add_argument("--splits_cache", type=str, default=r"C:\Users\HP\.gemini\antigravity\scratch\stainshift\data\splits.json")
    parser.add_argument("--output_json", type=str, default=None)
    parser.add_argument("--batch_size", type=int, default=32)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    run_stress_test(
        checkpoint_path=args.checkpoint,
        data_dir=args.data_dir,
        splits_cache=args.splits_cache,
        output_json=args.output_json,
        batch_size=args.batch_size,
        device=device
    )
