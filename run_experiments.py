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
from src.tracking import MLflowTracker, get_git_commit
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
    parser.add_argument(
        "--stage",
        type=str,
        default="all",
        choices=["all", "train_only", "eval_only"],
        help="Execution stage: train_only (Stage A: train & select), eval_only (Stage B: test evaluation), or all"
    )
    parser.add_argument(
        "--include_legacy_aliases",
        action="store_true",
        help="Include legacy scanner aliases in evaluation (default evaluates only the 8 distinct scientific conditions)"
    )
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    parser.add_argument("--max_samples_per_class", type=int, default=None, help="Limit samples per class for bounded smoke tests")
    parser.add_argument("--arch", type=str, default="mobilenet_v3_small", choices=["mobilenet_v3_small", "resnet18"])
    parser.add_argument("--no_pretrained", action="store_true", help="Initialize models with random weights instead of downloading torchvision weights")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration and paths without training")
    # MLflow arguments
    parser.add_argument("--use_mlflow", action="store_true", help="Enable MLflow experiment tracking")
    parser.add_argument("--mlflow_tracking_uri", type=str, default=os.getenv("MLFLOW_TRACKING_URI"), help="MLflow tracking URI")
    parser.add_argument("--mlflow_artifact_root", type=str, default=os.getenv("MLFLOW_ARTIFACT_ROOT"), help="MLflow artifact storage root directory")
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
            artifact_location=args.mlflow_artifact_root,
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
            params_to_log = {
                "checkpoint_policy": args.checkpoint_policy,
                "architecture": args.arch,
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "lr": args.lr,
                "seed": args.seed,
                "device": args.device,
                "data_dir": str(data_dir),
                "splits_cache": str(splits_cache),
            }
            manifest_file = data_dir / "frozen_final_split_manifest.json"
            if manifest_file.is_file():
                import hashlib
                with open(manifest_file, "rb") as mf:
                    mf_sha256 = hashlib.sha256(mf.read()).hexdigest()
                params_to_log["split_manifest_path"] = str(manifest_file)
                params_to_log["split_manifest_sha256"] = mf_sha256
                tracker.log_artifact(manifest_file)
            if splits_cache.is_file():
                tracker.log_artifact(splits_cache)

            tracker.log_params(params_to_log)


        baseline_ckpt = models_dir / "baseline.pth"
        robust_ckpt = models_dir / "robust_stain_aug.pth"

        # -----------------------------------------------------------------
        # STAGE A: Training and Checkpoint Selection (Train + Val splits)
        # -----------------------------------------------------------------
        if args.stage in ["all", "train_only"]:
            # Step 1: Baseline Model
            should_train_baseline = args.checkpoint_policy == "train_new" or (
                args.checkpoint_policy == "reuse_if_valid" and not baseline_ckpt.is_file()
            )

            if should_train_baseline:
                print("\n>>> [1/2] Training BASELINE Model (Standard Data Pipeline)...")
                run_training(
                    data_dir=data_dir,
                    splits_cache=splits_cache,
                    output_dir=models_dir,
                    model_name="baseline",
                    train_mode="train_standard",
                    arch=args.arch,
                    pretrained=not args.no_pretrained,
                    epochs=args.epochs,
                    batch_size=args.batch_size,
                    lr=args.lr,
                    device=args.device,
                    seed=args.seed,
                    max_samples_per_class=args.max_samples_per_class,
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
                print("\n>>> [2/2] Training STAIN-ROBUST Model (Beer-Lambert Stain Augmentation)...")
                run_training(
                    data_dir=data_dir,
                    splits_cache=splits_cache,
                    output_dir=models_dir,
                    model_name="robust_stain_aug",
                    train_mode="train_stain_augmented",
                    arch=args.arch,
                    pretrained=not args.no_pretrained,
                    epochs=args.epochs,
                    batch_size=args.batch_size,
                    lr=args.lr,
                    device=args.device,
                    seed=args.seed,
                    max_samples_per_class=args.max_samples_per_class,
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

            if args.stage == "train_only":
                print(f"\n[STAGE A COMPLETE] Models trained and checkpoints verified at: {models_dir}")
                print(f"Held-out test set evaluation is preserved and deferred to Stage B (--stage eval_only).")
                return

        # -----------------------------------------------------------------
        # STAGE B: Held-Out Final Evaluation (Test split only)
        # -----------------------------------------------------------------
        if not baseline_ckpt.is_file():
            raise FileNotFoundError(f"Baseline checkpoint not found for evaluation: {baseline_ckpt}")
        if not robust_ckpt.is_file():
            raise FileNotFoundError(f"Robust checkpoint not found for evaluation: {robust_ckpt}")

        distinct_only = not args.include_legacy_aliases

        # Step 3: Stress-test Baseline Model
        print("\n>>> [1/2] Stress-testing BASELINE model on held-out test split...")
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
            distinct_only=distinct_only,
        )

        # Step 4: Stress-test Stain-Robust Model
        print("\n>>> [2/2] Stress-testing STAIN-ROBUST model on held-out test split...")
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
            distinct_only=distinct_only,
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
                "distinct_only": distinct_only,
            },
            "profiles": {}
        }

        for profile in baseline_results["profiles"].keys():
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
                "description": b_prof.get("description", profile)
            }

            b_drop_str = f"{b_drop:+.2f}%" if profile != "original" else "0.00% (Ref)"
            r_drop_str = f"{r_drop:+.2f}%" if profile != "original" else "0.00% (Ref)"
            rec_str = f"{recovery:+.2f}%" if profile != "original" else f"({r_acc - b_acc:+.2f}%)"
            print(f"{profile:<24} | {b_acc:>10.2f}% | {b_drop_str:>13} | {r_acc:>10.2f}% | {r_drop_str:>13} | {rec_str:>10}")

        comparison_path = exp_dir / "comparison_summary.json"
        with open(comparison_path, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2)

        # Export accuracy-by-condition CSV
        csv_path = exp_dir / "accuracy_by_condition.csv"
        import csv
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["condition", "baseline_acc", "baseline_drop_pct", "robust_acc", "robust_drop_pct", "recovery_pct"])
            for prof, pdata in comparison["profiles"].items():
                writer.writerow([prof, pdata["baseline_acc"], pdata["baseline_drop"], pdata["robust_acc"], pdata["robust_drop"], pdata["recovery"]])

        # Generate Benchmark Manifest linking results, MLflow ID, hashes, and timestamp
        import hashlib
        import datetime

        def compute_sha256(p: Path) -> str:
            if not p.is_file():
                return "missing"
            with open(p, "rb") as bf:
                return hashlib.sha256(bf.read()).hexdigest()

        split_manifest_path = data_dir / "frozen_final_split_manifest.json"
        benchmark_manifest = {
            "benchmark_version": "1.0.0",
            "evaluation_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "mlflow_run_id": tracker.run_id if (tracker and tracker.enabled) else "standalone",
            "git_commit": get_git_commit(),
            "dataset_root": str(data_dir),
            "split_manifest": {
                "path": str(split_manifest_path),
                "sha256": compute_sha256(split_manifest_path),
            },
            "splits_cache": {
                "path": str(splits_cache),
                "sha256": compute_sha256(splits_cache),
            },
            "checkpoints": {
                "baseline": {
                    "path": str(baseline_ckpt),
                    "sha256": compute_sha256(baseline_ckpt),
                },
                "robust_stain_aug": {
                    "path": str(robust_ckpt),
                    "sha256": compute_sha256(robust_ckpt),
                },
            },
            "conditions_evaluated": list(comparison["profiles"].keys()),
            "results_summary": comparison["profiles"],
        }
        manifest_path = exp_dir / "benchmark_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_manifest, f, indent=2)

        print(f"\nAll experiments complete!")
        print(f"  Comparison JSON:    {comparison_path}")
        print(f"  Accuracy CSV:       {csv_path}")
        print(f"  Benchmark Manifest: {manifest_path}")

        if tracker and tracker.enabled:
            tracker.log_artifact(comparison_path)
            tracker.log_artifact(csv_path)
            tracker.log_artifact(manifest_path)



if __name__ == "__main__":
    main()
