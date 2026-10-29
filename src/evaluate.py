"""
StainShift: Model Stress-Testing & Robustness Evaluation
Quantifies model performance degradation under physical stain shifts and scanner variations.
Supports optional MLflow tracking.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from sklearn.metrics import classification_report, accuracy_score, f1_score
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from .dataset import CRCDataset, get_data_splits
from .models import CLASS_NAMES, load_checkpoint
from .stain_shift import STAIN_PROFILES
from .tracking import MLflowTracker

logger = logging.getLogger(__name__)


@torch.no_grad()
def evaluate_stain_profile(
    model: torch.nn.Module,
    file_paths: List[str],
    labels: List[int],
    profile_name: str,
    batch_size: int = 32,
    device: str = "cpu",
    fail_mode: str = "fallback_and_record",
) -> Dict[str, Any]:
    """
    Evaluates the model on test patches under a specific stain shift profile.
    Tracks transformation attempts, successes, skips, and failures.
    """
    dev = torch.device(device)
    transform_mode = "eval_reconstruction" if profile_name == "reconstruction_only" else "eval_shifted"

    dataset = CRCDataset(
        file_paths=file_paths,
        labels=labels,
        transform_mode=transform_mode,
        stain_profile=profile_name if profile_name != "reconstruction_only" else "original",
        fail_mode=fail_mode,
    )
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    model.eval()
    all_preds: List[int] = []
    all_targets: List[int] = []
    all_confs: List[float] = []

    for images, targets, _ in loader:
        images = images.to(dev)
        outputs = model(images)
        probs = F.softmax(outputs, dim=1)
        confs, preds = torch.max(probs, dim=1)

        all_preds.extend(preds.cpu().numpy().tolist())
        all_targets.extend(targets.numpy().tolist())
        all_confs.extend(confs.cpu().numpy().tolist())

    acc = float(accuracy_score(all_targets, all_preds))
    f1 = float(f1_score(all_targets, all_preds, average="macro", zero_division=0))
    mean_conf = float(np.mean(all_confs)) if all_confs else 0.0

    report = classification_report(
        all_targets,
        all_preds,
        labels=list(range(len(CLASS_NAMES))),
        target_names=CLASS_NAMES,
        output_dict=True,
        zero_division=0
    )

    return {
        "accuracy": acc,
        "macro_f1": f1,
        "mean_confidence": mean_conf,
        "evaluated_count": len(all_preds),
        "transform_stats": dict(dataset.transform_stats),
        "classification_report": report,
        "predictions": all_preds,
    }


def run_stress_test(
    checkpoint_path: Union[str, Path],
    data_dir: Union[str, Path],
    splits_cache: Optional[Union[str, Path]] = None,
    output_json: Optional[Union[str, Path]] = None,
    batch_size: int = 32,
    device: str = "cpu",
    expected_arch: Optional[str] = "mobilenet_v3_small",
    allow_legacy: bool = True,
    dry_run: bool = False,
    tracker: Optional[MLflowTracker] = None,
) -> Dict[str, Any]:
    """
    Stress-tests a model checkpoint across all benchmark stain profiles.

    Reports:
    - Reference baseline (exact original pixels)
    - Reconstruction-only control (isolating deconvolution reconstruction loss)
    - Synthetic stain shifts (perturbation effects)
    - Prediction change rates and transformation statistics
    """
    ckpt_path = Path(checkpoint_path)
    data_path = Path(data_dir)

    print(f"=== Stress-Testing Checkpoint: {ckpt_path} ===")

    if dry_run:
        print("[DRY-RUN] Verifying arguments and environment without running evaluation.")
        if not ckpt_path.is_file():
            raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")
        if not data_path.is_dir():
            raise FileNotFoundError(f"Dataset directory not found: {data_path}")
        print(f"[DRY-RUN] Verified checkpoint and dataset paths.")
        return {"dry_run": True, "checkpoint": str(ckpt_path), "data_dir": str(data_path)}

    model, ckpt_meta = load_checkpoint(
        ckpt_path,
        expected_arch=expected_arch,
        expected_classes=CLASS_NAMES,
        device=device,
        allow_legacy=allow_legacy,
    )

    if tracker and tracker.enabled:
        tracker.log_params({
            "eval_checkpoint": str(ckpt_path),
            "eval_provenance": ckpt_meta.get("provenance", "unknown"),
            "eval_architecture": ckpt_meta.get("architecture", expected_arch),
            "eval_device": str(device),
            "eval_batch_size": batch_size,
        })

    _, _, test_split = get_data_splits(data_path, splits_cache=splits_cache)
    file_paths = test_split["files"]
    labels = test_split["labels"]
    print(f"Evaluating across {len(file_paths)} test patches for {len(STAIN_PROFILES)} stain regimes...")

    results: Dict[str, Any] = {
        "metadata": {
            "checkpoint_path": str(ckpt_path),
            "checkpoint_provenance": ckpt_meta.get("provenance", "unknown"),
            "architecture": ckpt_meta.get("architecture", expected_arch),
            "dataset_dir": str(data_path),
            "test_sample_count": len(file_paths),
            "device": str(device),
        },
        "profiles": {}
    }

    baseline_acc: Optional[float] = None
    baseline_f1: Optional[float] = None
    baseline_preds: Optional[List[int]] = None

    for profile_name, info in STAIN_PROFILES.items():
        print(f"\nEvaluating Profile: [{profile_name}] - {info['description']}...")
        metrics = evaluate_stain_profile(
            model=model,
            file_paths=file_paths,
            labels=labels,
            profile_name=profile_name,
            batch_size=batch_size,
            device=device,
        )

        acc = metrics["accuracy"]
        f1 = metrics["macro_f1"]
        current_preds = metrics["predictions"]

        if profile_name == "original":
            baseline_acc = acc
            baseline_f1 = f1
            baseline_preds = current_preds
            delta_acc = 0.0
            delta_f1 = 0.0
            flip_rate = 0.0
        else:
            delta_acc = (acc - baseline_acc) * 100.0 if baseline_acc is not None else 0.0
            delta_f1 = (f1 - baseline_f1) if baseline_f1 is not None else 0.0
            if baseline_preds is not None and len(baseline_preds) == len(current_preds):
                flips = sum(1 for p1, p2 in zip(baseline_preds, current_preds) if p1 != p2)
                flip_rate = (flips / max(len(baseline_preds), 1)) * 100.0
            else:
                flip_rate = 0.0

        metrics["delta_acc_pct"] = round(delta_acc, 2)
        metrics["delta_f1"] = round(delta_f1, 4)
        metrics["prediction_flip_rate_pct"] = round(flip_rate, 2)

        # Log to tracker
        if tracker and tracker.enabled:
            tracker.log_eval_metrics(profile_name, metrics)
            tracker.log_dict_artifact(
                metrics["classification_report"],
                f"reports/classification_report_{profile_name}.json"
            )

        # Do not keep raw large prediction list in saved JSON summary
        metrics.pop("predictions", None)

        results["profiles"][profile_name] = metrics

        delta_str = f"({delta_acc:+.2f}%)" if profile_name != "original" else "(Reference)"
        flip_str = f"| Flips: {flip_rate:.1f}%" if profile_name != "original" else ""
        print(
            f"  -> Accuracy: {acc*100:.2f}% {delta_str} | Macro F1: {f1:.4f} {flip_str} | "
            f"Failures: {metrics['transform_stats']['failures']}"
        )

    if output_json:
        out_p = Path(output_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nFull stress test report written to: {out_p}")
        if tracker and tracker.enabled:
            tracker.log_artifact(out_p)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StainShift Model Stress Testing")
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to model checkpoint (.pth)")
    parser.add_argument("--data_dir", type=str, default="data/CRC-VAL-HE-7K-png", help="Path to patch dataset directory")
    parser.add_argument("--splits_cache", type=str, default="data/splits.json", help="Path to splits JSON file")
    parser.add_argument("--output_json", type=str, default=None, help="Path to save evaluation JSON results")
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--arch", type=str, default="mobilenet_v3_small", choices=["mobilenet_v3_small", "resnet18"])
    parser.add_argument("--allow_legacy", action="store_true", default=True, help="Allow loading legacy checkpoints")
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--dry-run", action="store_true", help="Validate setup without executing evaluation")
    # MLflow arguments
    parser.add_argument("--use_mlflow", action="store_true", help="Enable MLflow experiment tracking")
    parser.add_argument("--mlflow_tracking_uri", type=str, default=os.getenv("MLFLOW_TRACKING_URI"), help="MLflow tracking URI")
    parser.add_argument("--mlflow_experiment_name", type=str, default=os.getenv("MLFLOW_EXPERIMENT_NAME", "stainshift_benchmark"), help="MLflow experiment name")
    parser.add_argument("--run_type", type=str, default="smoke_test", choices=["smoke_test", "full_experiment"], help="Label run as smoke_test or full_experiment")
    args = parser.parse_args()

    tracker = None
    if args.use_mlflow:
        ckpt_stem = Path(args.checkpoint).stem
        tracker = MLflowTracker(
            enabled=True,
            tracking_uri=args.mlflow_tracking_uri,
            experiment_name=args.mlflow_experiment_name,
            run_name=f"stress_test_{ckpt_stem}",
            run_type=args.run_type,
        )

    with tracker if tracker else nullcontext():
        run_stress_test(
            checkpoint_path=args.checkpoint,
            data_dir=args.data_dir,
            splits_cache=args.splits_cache,
            output_json=args.output_json,
            batch_size=args.batch_size,
            device=args.device,
            expected_arch=args.arch,
            allow_legacy=args.allow_legacy,
            dry_run=args.dry_run,
            tracker=tracker,
        )
