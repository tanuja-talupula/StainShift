"""
StainShift Master Experiment Runner
Trains both Baseline and Stain-Robust models on the Zenodo CRC-VAL-HE-7K dataset,
stress-tests them across 7 real-world and synthetic stain-shift regimes,
and answers: 'Does the model still work when the stain colour changes?'
"""

import os
import sys
import json
import time

# Ensure proper paths
BASE_DIR = r"C:\Users\HP\.gemini\antigravity\scratch\stainshift"
os.environ["TORCH_HOME"] = r"C:\Users\HP\.gemini\antigravity\scratch\torch_cache"
sys.path.append(BASE_DIR)

from src.train import run_training
from src.evaluate import run_stress_test
from src.stain_shift import STAIN_PROFILES


def main():
    data_dir = os.path.join(BASE_DIR, "data", "CRC-VAL-HE-7K-png")
    splits_cache = os.path.join(BASE_DIR, "data", "splits.json")
    models_dir = os.path.join(BASE_DIR, "models")
    exp_dir = os.path.join(BASE_DIR, "experiments")
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(exp_dir, exist_ok=True)

    print("=================================================================")
    print(" PROJECT: StainShift — Histopathology Domain Shift Benchmark")
    print(" Dataset: Zenodo 1214456 (CRC-VAL-HE-7K: 7,180 patches, 9 classes)")
    print("=================================================================\n")

    # Step 1: Train Baseline Model (Geometric augmentation only, no stain defense)
    baseline_ckpt = os.path.join(models_dir, "baseline.pth")
    if not os.path.exists(baseline_ckpt):
        print("\n>>> [1/4] Training BASELINE Model (Standard Data Pipeline)...")
        run_training(
            data_dir=data_dir,
            splits_cache=splits_cache,
            output_dir=models_dir,
            model_name="baseline",
            train_mode="train_standard",
            epochs=3,
            batch_size=32,
            lr=3e-4,
            device="cpu"
        )
    else:
        print(f">>> Found existing baseline checkpoint at: {baseline_ckpt}")

    # Step 2: Train Robust Model (With on-the-fly Beer-Lambert Stain Augmentation)
    robust_ckpt = os.path.join(models_dir, "robust_stain_aug.pth")
    if not os.path.exists(robust_ckpt):
        print("\n>>> [2/4] Training STAIN-ROBUST Model (Beer-Lambert Stain Augmentation)...")
        run_training(
            data_dir=data_dir,
            splits_cache=splits_cache,
            output_dir=models_dir,
            model_name="robust_stain_aug",
            train_mode="train_stain_augmented",
            epochs=3,
            batch_size=32,
            lr=3e-4,
            device="cpu"
        )
    else:
        print(f">>> Found existing robust checkpoint at: {robust_ckpt}")

    # Step 3: Stress-test Baseline Model
    print("\n>>> [3/4] Stress-testing BASELINE model across all stain regimes...")
    baseline_results = run_stress_test(
        checkpoint_path=baseline_ckpt,
        data_dir=data_dir,
        splits_cache=splits_cache,
        output_json=os.path.join(exp_dir, "baseline_stress_test.json"),
        batch_size=32,
        device="cpu"
    )

    # Step 4: Stress-test Stain-Robust Model
    print("\n>>> [4/4] Stress-testing STAIN-ROBUST model across all stain regimes...")
    robust_results = run_stress_test(
        checkpoint_path=robust_ckpt,
        data_dir=data_dir,
        splits_cache=splits_cache,
        output_json=os.path.join(exp_dir, "robust_stress_test.json"),
        batch_size=32,
        device="cpu"
    )

    # Step 5: Generate Comparison Summary
    print("\n=================================================================")
    print("                    FINAL COMPARISON RESULTS                     ")
    print("=================================================================")
    header = f"{'Stain Profile':<22} | {'Baseline Acc':<12} | {'Baseline Drop':<13} | {'Robust Acc':<12} | {'Robust Drop':<13} | {'Recovery':<10}"
    print(header)
    print("-" * len(header))

    comparison = {}
    for profile in STAIN_PROFILES.keys():
        b_acc = baseline_results[profile]["accuracy"] * 100.0
        b_drop = baseline_results[profile]["delta_acc_pct"]
        r_acc = robust_results[profile]["accuracy"] * 100.0
        r_drop = robust_results[profile]["delta_acc_pct"]
        recovery = r_acc - b_acc

        comparison[profile] = {
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
        print(f"{profile:<22} | {b_acc:>10.2f}% | {b_drop_str:>13} | {r_acc:>10.2f}% | {r_drop_str:>13} | {rec_str:>10}")

    comparison_path = os.path.join(exp_dir, "comparison_summary.json")
    with open(comparison_path, "w") as f:
        json.dump(comparison, f, indent=2)

    print(f"\nAll experiments complete! Comparison saved to: {comparison_path}")


if __name__ == "__main__":
    main()
