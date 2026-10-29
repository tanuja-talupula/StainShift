"""
StainShift Master Experiment Runner
Trains both Baseline and Stain-Robust models on the CRC dataset,
stress-tests them across benchmark stain-shift regimes,
and generates standardized scientific comparison reports.
Supports optional MLflow experiment tracking.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict

import torch

# Ensure repo root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluate import run_stress_test
from src.models import load_checkpoint
from src.stain_shift import STAIN_PROFILES
from src.tracking import MLflowTracker
from src.train import run_training

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="StainShift Master Experiment Runner")
    parser.add_argument("--data_dir", type=str, default="data/CRC-VAL-HE-7K-png", help="Path to patch dataset directory")
    parser.add_argument("--splits_cache", type=str, default="data/splits.json", help="Path to splits JSON file")
    parser.add_argument("--models_dir", type=str, default="models", help="Directory where models are saved/loaded")
    parser.add_argument("--exp_dir", type=str, default="experiments", help="Directory where experiment reports are written")
    parser.add_argument(
        "--checkpoint_policy",
        type=str,
        default="reuse_if_valid",
        choices=["train_new", "reuse_if_valid", "eval_only"],
        help="Checkpoint management policy (prevents silent stale reuse)"
    )
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    parser.add_argument("--arch", type=str, default="mobilenet_v3_small", choices=["mobilenet_v3_small", "resnet18"])
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration and paths without training")
    # MLflow arguments
    parser.add_argument("--use_mlflow", action="store_true", help="Enable MLflow experiment tracking")
    parser.add_argument("--mlflow_tracking_uri", type=str, default=os.getenv("MLFLOW_TRACKING_URI"), help="MLflow tracking URI")
    parser.add_argument("--mlflow_experiment_name", type=str, default=os.getenv("MLFLOW_EXPERIMENT_NAME", "stainshift_benchmark"), help="MLflow experiment name")
    parser.add_argument("--run_type", type=str, default="smoke_test", choices=["smoke_test", "full_experiment"], help="Label run as smoke_test or full_experiment")
    parser.add_argument("--log_models_to_mlflow", action="store_true", help="Explicitly log checkpoint weights to MLflow")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    splits_cache = Path(args.splits_cache)
    models_dir = Path(args.models_dir)
    exp_dir = Path(args.exp_dir)

    models_dir.mkdir(parents=True, exist_ok=True)
    exp_dir.mkdir(parents=True, exist_ok=True)

    print("=================================================================")
    print(" PROJECT: StainShift — Histopathology Domain Shift Benchmark")
    print(f" Working Directory: {PROJECT_ROOT}")
    print(f" Checkpoint Policy: {args.checkpoint_policy} | Device: {args.device} | Seed: {args.seed}")
    if args.use_mlflow:
        print(f" MLflow Tracking: ENABLED (Experiment: {args.mlflow_experiment_name}, Run Type: {args.run_type})")
    print("=================================================================\n")

    if args.dry_run:
        print("[DRY-RUN] Validating directories and CLI arguments...")
        print(f"  Data dir: {data_dir} (Exists: {data_dir.is_dir()})")
        print(f"  Splits cache: {splits_cache}")
        print(f"  Models dir: {models_dir}")
        print(f"  Exp dir: {exp_dir}")
        print(f"  MLflow tracking enabled: {args.use_mlflow}")
        print("[DRY-RUN] Configuration check passed successfully.")
        return

    tracker = None
    if args.use_mlflow:
        tracker = MLflowTracker(
            enabled=True,
            tracking_uri=args.mlflow_tracking_uri,
            experiment_name=args.mlflow_experiment_name,
            run_name="stainshift_benchmark_run",
            run_type=args.run_type,
            log_checkpoints=args.log_models_to_mlflow,
            tags={
                "checkpoint_policy": args.checkpoint_policy,
                "architecture": args.arch,
                "dataset": data_dir.name,
                "seed": args.seed,
            }
        )

    with tracker if tracker else nullcontext():
        if tracker and tracker.enabled:
            tracker.log_params({
                "checkpoint_policy": args.checkpoint_policy,
                "architecture": args.arch,
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "lr": args.lr,
                "seed": args.seed,
                "device": args.device,
                "data_dir": str(data_dir),
                "splits_cache": str(splits_cache),
            })

        baseline_ckpt = models_dir / "baseline.pth"
        robust_ckpt = models_dir / "robust_stain_aug.pth"

        # Step 1: Baseline Model
        should_train_baseline = args.checkpoint_policy == "train_new" or (
            args.checkpoint_policy == "reuse_if_valid" and not baseline_ckpt.is_file()
        )

        if should_train_baseline:
            print("\n>>> [1/4] Training BASELINE Model (Standard Data Pipeline)...")
            run_training(
                data_dir=data_dir,
                splits_cache=splits_cache,
                output_dir=models_dir,
                model_name="baseline",
                train_mode="train_standard",
                arch=args.arch,
                epochs=args.epochs,
                batch_size=args.batch_size,
                lr=args.lr,
                device=args.device,
                seed=args.seed,
                tracker=tracker,
                log_models_to_mlflow=args.log_models_to_mlflow,
            )
        else:
            if not baseline_ckpt.is_file():
                raise FileNotFoundError(
                    f"Checkpoint policy is '{args.checkpoint_policy}', but baseline checkpoint does not exist at: {baseline_ckpt}"
                )
            print(f">>> Reusing existing baseline checkpoint at: {baseline_ckpt}")
            load_checkpoint(baseline_ckpt, expected_arch=args.arch, device="cpu", allow_legacy=True)

        # Step 2: Robust Model
        should_train_robust = args.checkpoint_policy == "train_new" or (
            args.checkpoint_policy == "reuse_if_valid" and not robust_ckpt.is_file()
        )

        if should_train_robust:
            print("\n>>> [2/4] Training STAIN-ROBUST Model (Beer-Lambert Stain Augmentation)...")
            run_training(
                data_dir=data_dir,
                splits_cache=splits_cache,
                output_dir=models_dir,
                model_name="robust_stain_aug",
                train_mode="train_stain_augmented",
                arch=args.arch,
                epochs=args.epochs,
                batch_size=args.batch_size,
                lr=args.lr,
                device=args.device,
                seed=args.seed,
                tracker=tracker,
                log_models_to_mlflow=args.log_models_to_mlflow,
            )
        else:
            if not robust_ckpt.is_file():
                raise FileNotFoundError(
                    f"Checkpoint policy is '{args.checkpoint_policy}', but robust checkpoint does not exist at: {robust_ckpt}"
                )
            print(f">>> Reusing existing robust checkpoint at: {robust_ckpt}")
            load_checkpoint(robust_ckpt, expected_arch=args.arch, device="cpu", allow_legacy=True)

        # Step 3: Stress-test Baseline Model
        print("\n>>> [3/4] Stress-testing BASELINE model across all stain regimes...")
        baseline_results = run_stress_test(
            checkpoint_path=baseline_ckpt,
            data_dir=data_dir,
            splits_cache=splits_cache,
            output_json=exp_dir / "baseline_stress_test.json",
            batch_size=args.batch_size,
            device=args.device,
            expected_arch=args.arch,
            allow_legacy=True,
            tracker=tracker,
        )

        # Step 4: Stress-test Stain-Robust Model
        print("\n>>> [4/4] Stress-testing STAIN-ROBUST model across all stain regimes...")
        robust_results = run_stress_test(
            checkpoint_path=robust_ckpt,
            data_dir=data_dir,
            splits_cache=splits_cache,
            output_json=exp_dir / "robust_stress_test.json",
            batch_size=args.batch_size,
            device=args.device,
            expected_arch=args.arch,
            allow_legacy=True,
            tracker=tracker,
        )

        # Step 5: Generate Comparison Summary
        print("\n=================================================================")
        print("                    FINAL COMPARISON RESULTS                     ")
        print("=================================================================")
        header = (
            f"{'Stain Profile':<24} | {'Baseline Acc':<12} | {'Baseline Drop':<13} | "
            f"{'Robust Acc':<12} | {'Robust Drop':<13} | {'Recovery':<10}"
        )
        print(header)
        print("-" * len(header))

        comparison: Dict[str, Any] = {
            "metadata": {
                "baseline_checkpoint": str(baseline_ckpt),
                "robust_checkpoint": str(robust_ckpt),
                "checkpoint_policy": args.checkpoint_policy,
                "architecture": args.arch,
                "seed": args.seed,
                "device": args.device,
            },
            "profiles": {}
        }

        for profile in STAIN_PROFILES.keys():
            b_prof = baseline_results["profiles"][profile]
            r_prof = robust_results["profiles"][profile]

            b_acc = b_prof["accuracy"] * 100.0
            b_drop = b_prof["delta_acc_pct"]
            r_acc = r_prof["accuracy"] * 100.0
            r_drop = r_prof["delta_acc_pct"]
            recovery = r_acc - b_acc

            comparison["profiles"][profile] = {
                "baseline_acc": round(b_acc, 2),
                "baseline_drop": round(b_drop, 2),
                "robust_acc": round(r_acc, 2),
                "robust_drop": round(r_drop, 2),
                "recovery": round(recovery, 2),
                "description": STAIN_PROFILES[profile]["description"]
            }

            b_drop_str = f"{b_drop:+.2f}%" if profile != "original" else "0.00% (Ref)"
            r_drop_str = f"{r_drop:+.2f}%" if profile != "original" else "0.00% (Ref)"
            rec_str = f"{recovery:+.2f}%" if profile != "original" else f"({r_acc - b_acc:+.2f}%)"
            print(f"{profile:<24} | {b_acc:>10.2f}% | {b_drop_str:>13} | {r_acc:>10.2f}% | {r_drop_str:>13} | {rec_str:>10}")

        comparison_path = exp_dir / "comparison_summary.json"
        with open(comparison_path, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2)

        print(f"\nAll experiments complete! Comparison saved to: {comparison_path}")

        if tracker and tracker.enabled:
            tracker.log_artifact(comparison_path)


if __name__ == "__main__":
    main()
