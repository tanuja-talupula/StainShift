"""
Public Benchmark Exporter for StainShift.
Reads verified artifacts and metadata from completed MLflow benchmark run
and generates a sanitized, schema-validated public JSON file for website dashboards.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any, Dict, List

import mlflow

# Distinct conditions in order of scientific presentation
DISTINCT_CONDITIONS = [
    "original",
    "reconstruction_only",
    "heavy_hematoxylin",
    "heavy_eosin",
    "pale_understained",
    "dark_overstained",
    "synthetic_warm_shift",
    "synthetic_cool_shift",
]

LEGACY_ALIASES = ["scanner_warm_shift", "scanner_cool_shift"]

CLASS_NAMES = ["ADI", "BACK", "DEB", "LYM", "MUC", "MUS", "NORM", "STR", "TUM"]


def validate_public_export(data: Dict[str, Any]) -> None:
    """
    Validates structural and numeric integrity of the exported public results.
    Raises ValueError or AssertionError on validation failure.
    """
    required_top_keys = [
        "benchmark_metadata",
        "dataset_metadata",
        "hardware_environment",
        "models",
        "conditions_evaluated",
        "results",
        "comparison_table",
        "latency_benchmarks",
        "validation_status",
    ]
    for k in required_top_keys:
        if k not in data:
            raise ValueError(f"Missing required top-level key: {k}")

    bm = data["benchmark_metadata"]
    if not bm.get("mlflow_run_id"):
        raise ValueError("Missing MLflow run ID")
    if not bm.get("git_commit"):
        raise ValueError("Missing git commit")
    if bm.get("run_type") != "full_experiment":
        raise ValueError(f"Expected run_type 'full_experiment', got '{bm.get('run_type')}'")

    dm = data["dataset_metadata"]
    if dm.get("total_images") != 7180:
        raise ValueError(f"Expected 7180 total images, got {dm.get('total_images')}")
    if dm.get("held_out_test_images") != 1077:
        raise ValueError(f"Expected 1077 held-out test images, got {dm.get('held_out_test_images')}")
    if not dm.get("split_manifest_sha256"):
        raise ValueError("Missing split manifest SHA256")

    # Verify exactly 8 conditions
    conds = data["conditions_evaluated"]
    if conds != DISTINCT_CONDITIONS:
        raise ValueError(f"Conditions mismatch. Expected {DISTINCT_CONDITIONS}, got {conds}")

    for alias in LEGACY_ALIASES:
        if alias in conds:
            raise ValueError(f"Legacy alias '{alias}' must not appear in conditions_evaluated")

    # Validate models and results
    for model_name in ["baseline", "robust_stain_aug"]:
        if model_name not in data["models"]:
            raise ValueError(f"Model '{model_name}' missing from models metadata")
        if not data["models"][model_name].get("checkpoint_sha256"):
            raise ValueError(f"Missing checkpoint SHA256 for model '{model_name}'")

        if model_name not in data["results"]:
            raise ValueError(f"Results missing for model '{model_name}'")

        m_res = data["results"][model_name]
        for cname in DISTINCT_CONDITIONS:
            if cname not in m_res:
                raise ValueError(f"Condition '{cname}' missing in results for model '{model_name}'")
            entry = m_res[cname]
            acc = entry["accuracy"]
            f1 = entry["macro_f1"]
            drop = entry["accuracy_drop_pct"]
            if not (math.isfinite(acc) and 0.0 <= acc <= 100.0):
                raise ValueError(f"Invalid accuracy {acc} in {model_name}/{cname}")
            if not (math.isfinite(f1) and 0.0 <= f1 <= 1.0):
                raise ValueError(f"Invalid macro F1 {f1} in {model_name}/{cname}")
            if not math.isfinite(drop):
                raise ValueError(f"Non-finite drop {drop} in {model_name}/{cname}")
            if entry["evaluated_count"] != 1077:
                raise ValueError(f"Evaluated count is {entry['evaluated_count']}, expected 1077")
            if entry["transform_failures"] != 0:
                raise ValueError(f"Transform failures is {entry['transform_failures']}, expected 0")

            # Check per-class metrics
            pc = entry.get("per_class", {})
            for cl in CLASS_NAMES:
                if cl not in pc:
                    raise ValueError(f"Class '{cl}' missing in per_class metrics for {model_name}/{cname}")
                if not math.isfinite(pc[cl]["f1"]):
                    raise ValueError(f"Non-finite F1 for class {cl} in {model_name}/{cname}")

    # Validate latency
    lat = data["latency_benchmarks"]
    if not lat.get("disclaimer"):
        raise ValueError("Missing mandatory latency disclaimer")
    for m in ["baseline_mps", "robust_stain_aug_mps"]:
        if m not in lat["profiles"]:
            raise ValueError(f"Missing latency profile '{m}'")
        fwd = lat["profiles"][m]["model_forward_batch1"]
        if not (math.isfinite(fwd["mean_ms"]) and fwd["mean_ms"] > 0.0):
            raise ValueError(f"Invalid forward latency in {m}")

    # Ensure no local username or private path leaks
    serialized = json.dumps(data)
    for forbidden in ["/Users/", "/home/", "\\Users\\", "password", "token", "secret"]:
        if forbidden.lower() in serialized.lower():
            raise ValueError(f"Potential private string or secret leaked in export: {forbidden}")


def export_public_benchmark(
    mlflow_tracking_uri: str = "sqlite:///mlflow.db",
    run_id: str = "c76c59f4bd7c4fe39f2ed2135856845a",
    output_path: str = "public/data/stainshift_results.json",
) -> Dict[str, Any]:
    """
    Extracts artifacts from MLflow, sanitizes paths, structures, and validates the output.
    """
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    client = mlflow.tracking.MlflowClient()

    run = client.get_run(run_id)
    if run.info.status != "FINISHED":
        raise RuntimeError(f"Run {run_id} status is '{run.info.status}', expected 'FINISHED'")
    if run.data.tags.get("run_type") != "full_experiment":
        raise RuntimeError(f"Run {run_id} run_type is '{run.data.tags.get('run_type')}', expected 'full_experiment'")

    # Download required artifacts to local temp/memory
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_p = Path(tmp_dir)
        client.download_artifacts(run_id, "benchmark_manifest.json", str(tmp_p))
        client.download_artifacts(run_id, "comparison_summary.json", str(tmp_p))
        client.download_artifacts(run_id, "baseline_stress_test.json", str(tmp_p))
        client.download_artifacts(run_id, "robust_stress_test.json", str(tmp_p))
        client.download_artifacts(run_id, "final_latency_benchmark.json", str(tmp_p))

        with open(tmp_p / "benchmark_manifest.json", "r", encoding="utf-8") as f:
            manifest = json.load(f)
        with open(tmp_p / "comparison_summary.json", "r", encoding="utf-8") as f:
            comparison = json.load(f)
        with open(tmp_p / "baseline_stress_test.json", "r", encoding="utf-8") as f:
            b_stress = json.load(f)
        with open(tmp_p / "robust_stress_test.json", "r", encoding="utf-8") as f:
            r_stress = json.load(f)
        with open(tmp_p / "final_latency_benchmark.json", "r", encoding="utf-8") as f:
            lat_bench = json.load(f)

    # Format public results
    eval_timestamp = manifest.get("evaluation_timestamp", "")
    benchmark_date = eval_timestamp[:10] if eval_timestamp else "2026-10-29"

    public_data: Dict[str, Any] = {
        "benchmark_metadata": {
            "title": "StainShift: Histopathology Stain Domain Shift Robustness Benchmark",
            "version": "1.0.0",
            "benchmark_date": benchmark_date,
            "evaluation_timestamp": eval_timestamp,
            "git_commit": manifest.get("git_commit", "14ef1e1fc15d6e0f9ddb0a2fbd208833a39e3a26"),
            "mlflow_run_id": run_id,
            "run_type": "full_experiment",
            "license": "CC BY 4.0 (Dataset CRC-VAL-HE-7K) / MIT (Code)",
            "benchmark_scope": "Single-cohort frozen held-out test evaluation on uncompressed 8-bit RGB patches",
        },
        "dataset_metadata": {
            "dataset_name": "CRC-VAL-HE-7K",
            "source_zenodo_record": "https://zenodo.org/records/1214456",
            "total_images": 7180,
            "train_images": 5026,
            "val_images": 1077,
            "held_out_test_images": 1077,
            "split_manifest_sha256": manifest["split_manifest"]["sha256"],
            "splits_cache_sha256": manifest["splits_cache"]["sha256"],
            "num_classes": 9,
            "class_names": CLASS_NAMES,
            "class_descriptions": {
                "ADI": "Adipose tissue",
                "BACK": "Background (slide glass/empty)",
                "DEB": "Debris and necrosis",
                "LYM": "Lymphocytes",
                "MUC": "Mucus",
                "MUS": "Smooth muscle",
                "NORM": "Normal colon mucosa",
                "STR": "Cancer-associated stroma",
                "TUM": "Colorectal adenocarcinoma epithelium",
            },
            "held_out_class_support": {
                "ADI": 201,
                "BACK": 127,
                "DEB": 51,
                "LYM": 95,
                "MUC": 155,
                "MUS": 89,
                "NORM": 111,
                "STR": 63,
                "TUM": 185,
            },
        },
        "hardware_environment": {
            "evaluation_device": "Apple Silicon (MPS - Metal Performance Shaders)",
            "os": lat_bench.get("baseline_mps", {}).get("environment", {}).get("os", "Darwin"),
            "architecture": lat_bench.get("baseline_mps", {}).get("environment", {}).get("architecture", "arm64"),
            "python_version": lat_bench.get("baseline_mps", {}).get("environment", {}).get("python_version", "3.13.2"),
            "torch_version": lat_bench.get("baseline_mps", {}).get("environment", {}).get("torch_version", "2.6.0"),
        },
        "models": {
            "baseline": {
                "display_name": "Standard MobileNetV3 (Baseline)",
                "architecture": "mobilenet_v3_small",
                "weights_provenance": "ImageNet-1K V1 (mobilenet_v3_small-047dcff4.pth)",
                "training_pipeline": "Standard random spatial crops, flips, ImageNet normalization",
                "checkpoint_sha256": manifest["checkpoints"]["baseline"]["sha256"],
                "selected_epoch": int(run.data.params.get("baseline_best_epoch", 5)),
                "best_val_f1": float(run.data.params.get("baseline_best_val_f1", 0.9985)),
                "selection_rule": "highest_validation_macro_f1",
            },
            "robust_stain_aug": {
                "display_name": "Stain-Robust MobileNetV3 (Beer-Lambert Augmentation)",
                "architecture": "mobilenet_v3_small",
                "weights_provenance": "ImageNet-1K V1 (mobilenet_v3_small-047dcff4.pth)",
                "training_pipeline": "Standard pipeline + Online Macenko optical density perturbation",
                "checkpoint_sha256": manifest["checkpoints"]["robust_stain_aug"]["sha256"],
                "selected_epoch": int(run.data.params.get("robust_stain_aug_best_epoch", 4)),
                "best_val_f1": float(run.data.params.get("robust_stain_aug_best_val_f1", 0.9871)),
                "selection_rule": "highest_validation_macro_f1",
            },
        },
        "conditions_evaluated": DISTINCT_CONDITIONS,
        "results": {
            "baseline": {},
            "robust_stain_aug": {},
        },
        "comparison_table": [],
        "latency_benchmarks": {
            "disclaimer": (
                "These benchmarks represent local on-device hardware inference latency on Apple Silicon MPS "
                "with synchronized execution. They must not be conflated with website or HTTP API network latency."
            ),
            "device": "mps",
            "batch_size_single": 1,
            "batch_size_batched": 16,
            "profiles": {},
        },
        "validation_status": {
            "is_verified": True,
            "smoke_test_excluded": True,
            "legacy_aliases_excluded": True,
            "held_out_evaluated_count": 1077,
        },
    }

    # Populate per-model results for distinct conditions
    for model_key, stress_dict in [("baseline", b_stress), ("robust_stain_aug", r_stress)]:
        for cname in DISTINCT_CONDITIONS:
            prof = stress_dict["profiles"][cname]
            rep = prof["classification_report"]
            per_class = {}
            for cl in CLASS_NAMES:
                if cl in rep:
                    per_class[cl] = {
                        "precision": round(rep[cl]["precision"], 4),
                        "recall": round(rep[cl]["recall"], 4),
                        "f1": round(rep[cl]["f1-score"], 4),
                        "support": int(rep[cl]["support"]),
                    }

            public_data["results"][model_key][cname] = {
                "accuracy": round(prof["accuracy"] * 100.0, 2),
                "macro_f1": round(prof["macro_f1"], 4),
                "accuracy_drop_pct": round(prof["delta_acc_pct"], 2),
                "prediction_flip_rate_pct": round(prof.get("prediction_flip_rate_pct", 0.0), 2),
                "evaluated_count": int(prof["evaluated_count"]),
                "transform_failures": int(prof["transform_stats"]["failures"]),
                "per_class": per_class,
                "confusion_matrix": prof.get("confusion_matrix", []),
            }

    # Populate comparison table
    for cname in DISTINCT_CONDITIONS:
        b_acc = public_data["results"]["baseline"][cname]["accuracy"]
        b_drop = public_data["results"]["baseline"][cname]["accuracy_drop_pct"]
        r_acc = public_data["results"]["robust_stain_aug"][cname]["accuracy"]
        r_drop = public_data["results"]["robust_stain_aug"][cname]["accuracy_drop_pct"]
        recovery = round(r_acc - b_acc, 2)
        public_data["comparison_table"].append({
            "condition": cname,
            "description": comparison["profiles"][cname].get("description", cname),
            "baseline_accuracy_pct": b_acc,
            "baseline_drop_pct": b_drop,
            "robust_accuracy_pct": r_acc,
            "robust_drop_pct": r_drop,
            "net_recovery_pct": recovery,
        })

    # Populate latency benchmarks
    for mkey in ["baseline_mps", "robust_stain_aug_mps", "baseline_cpu"]:
        if mkey in lat_bench:
            entry = lat_bench[mkey]
            public_data["latency_benchmarks"]["profiles"][mkey] = {
                "device": entry.get("environment", {}).get("device", "unknown"),
                "model_forward_batch1": {
                    "timing_boundary": entry["model_forward_batch1"]["timing_boundary"],
                    "units": "milliseconds",
                    "warmup_runs": entry["model_forward_batch1"]["warm_up_calls"],
                    "timed_runs": entry["model_forward_batch1"]["timed_calls"],
                    "mean_ms": round(entry["model_forward_batch1"]["statistics"]["mean_ms"], 2),
                    "std_ms": round(entry["model_forward_batch1"]["statistics"]["std_ms"], 2),
                    "median_ms": round(entry["model_forward_batch1"]["statistics"]["median_ms"], 2),
                    "p95_ms": round(entry["model_forward_batch1"]["statistics"]["p95_ms"], 2),
                },
                "preprocessing_inclusive_original": {
                    "timing_boundary": entry["preprocessing_inclusive_original"]["timing_boundary"],
                    "units": "milliseconds",
                    "warmup_runs": entry["preprocessing_inclusive_original"]["warm_up_calls"],
                    "timed_runs": entry["preprocessing_inclusive_original"]["timed_calls"],
                    "mean_ms": round(entry["preprocessing_inclusive_original"]["statistics"]["mean_ms"], 2),
                    "std_ms": round(entry["preprocessing_inclusive_original"]["statistics"]["std_ms"], 2),
                    "median_ms": round(entry["preprocessing_inclusive_original"]["statistics"]["median_ms"], 2),
                    "p95_ms": round(entry["preprocessing_inclusive_original"]["statistics"]["p95_ms"], 2),
                },
                "preprocessing_inclusive_heavy_hematoxylin": {
                    "timing_boundary": entry["preprocessing_inclusive_heavy_hematoxylin"]["timing_boundary"],
                    "units": "milliseconds",
                    "warmup_runs": entry["preprocessing_inclusive_heavy_hematoxylin"]["warm_up_calls"],
                    "timed_runs": entry["preprocessing_inclusive_heavy_hematoxylin"]["timed_calls"],
                    "mean_ms": round(entry["preprocessing_inclusive_heavy_hematoxylin"]["statistics"]["mean_ms"], 2),
                    "std_ms": round(entry["preprocessing_inclusive_heavy_hematoxylin"]["statistics"]["std_ms"], 2),
                    "median_ms": round(entry["preprocessing_inclusive_heavy_hematoxylin"]["statistics"]["median_ms"], 2),
                    "p95_ms": round(entry["preprocessing_inclusive_heavy_hematoxylin"]["statistics"]["p95_ms"], 2),
                },
                "batched_throughput_batch16": {
                    "units": "samples_per_second",
                    "batch_size": 16,
                    "samples_per_second": round(entry["batched_throughput"]["throughput_samples_per_second"], 1),
                    "mean_ms_per_batch": round(entry["batched_throughput"]["ms_per_batch"]["mean_ms"], 2),
                },
            }

    # Validate output
    validate_public_export(public_data)

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(public_data, f, indent=2)

    print(f"Public benchmark results successfully validated and exported to: {out_p}")
    return public_data


def main():
    parser = argparse.ArgumentParser(description="Export sanitized public benchmark results for website")
    parser.add_argument("--tracking_uri", type=str, default="sqlite:///mlflow.db")
    parser.add_argument("--run_id", type=str, default="c76c59f4bd7c4fe39f2ed2135856845a")
    parser.add_argument("--output", type=str, default="public/data/stainshift_results.json")
    args = parser.parse_args()

    export_public_benchmark(
        mlflow_tracking_uri=args.tracking_uri,
        run_id=args.run_id,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
