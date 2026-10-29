"""
Freezes the final reproducible splits for CRC-VAL-HE-7K single-cohort benchmark.
Quarantines all 90 development smoke-test images into the training pool,
guaranteeing 100% held-out purity for the final test set.
"""

import json
from pathlib import Path
import random
from typing import Any, Dict

from src.dataset import scan_dataset_files, CLASS_NAMES


def main():
    data_dir = Path("data/CRC-VAL-HE-7K").resolve()
    scanned = scan_dataset_files(data_dir)

    # Load smoke-test manifest
    smoke_manifest_path = Path("smoke_test_experiments/smoke_test_split_manifest.json")
    with open(smoke_manifest_path, "r", encoding="utf-8") as f:
        smoke_manifest = json.load(f)
    smoke_ids = {s["image_id"] for s in smoke_manifest["samples"]}
    print(f"Quarantining {len(smoke_ids)} smoke-test image IDs away from validation and test sets.")

    seed = 42
    rng = random.Random(seed)

    final_manifest: Dict[str, Any] = {
        "metadata": {
            "dataset_name": "CRC-VAL-HE-7K",
            "dataset_root": str(data_dir),
            "protocol": "frozen_single_cohort_benchmark",
            "seed": seed,
            "total_images": 7180,
            "smoke_test_quarantine_count": len(smoke_ids),
            "smoke_test_quarantine_rule": "All 90 smoke-test images assigned to train pool; exactly 0 in val/test sets",
            "splits_ratio": {"train": 0.70, "val": 0.15, "test": 0.15},
            "class_names": CLASS_NAMES,
        },
        "split_counts": {},
        "samples": []
    }

    splits_cache_dict: Dict[str, Dict[str, list]] = {
        "train": {"files": [], "labels": []},
        "val": {"files": [], "labels": []},
        "test": {"files": [], "labels": []}
    }

    class_summary: Dict[str, Dict[str, int]] = {}

    for cidx, cname in enumerate(CLASS_NAMES):
        files = list(scanned[cname])
        files.sort(key=lambda p: p.relative_to(data_dir).as_posix())

        smoke_files = [p for p in files if p.name in smoke_ids]
        unexposed_files = [p for p in files if p.name not in smoke_ids]

        rng.shuffle(unexposed_files)

        n_total = len(files)
        n_test = max(1, int(round(n_total * 0.15)))
        n_val = max(1, int(round(n_total * 0.15)))
        n_train = n_total - n_test - n_val

        # Test and Val are drawn exclusively from unexposed files
        c_test = unexposed_files[:n_test]
        c_val = unexposed_files[n_test:n_test + n_val]
        # Train gets the remaining unexposed files + the smoke files
        c_train = unexposed_files[n_test + n_val:] + smoke_files

        assert len(c_train) == n_train
        assert len(c_val) == n_val
        assert len(c_test) == n_test

        # Verify disjointness
        s_train, s_val, s_test = set(c_train), set(c_val), set(c_test)
        assert s_train.isdisjoint(s_val)
        assert s_train.isdisjoint(s_test)
        assert s_val.isdisjoint(s_test)
        assert s_test.isdisjoint(set(smoke_files))
        assert s_val.isdisjoint(set(smoke_files))

        class_summary[cname] = {
            "total": n_total,
            "train": len(c_train),
            "val": len(c_val),
            "test": len(c_test),
            "smoke_quarantined_in_train": len(smoke_files)
        }

        for split_name, split_files in [("train", c_train), ("val", c_val), ("test", c_test)]:
            for p in split_files:
                rel = str(p.relative_to(data_dir))
                splits_cache_dict[split_name]["files"].append(rel)
                splits_cache_dict[split_name]["labels"].append(cidx)
                final_manifest["samples"].append({
                    "image_id": p.name,
                    "relative_path": rel,
                    "class_name": cname,
                    "class_index": cidx,
                    "split": split_name,
                    "was_in_smoke_test": p.name in smoke_ids
                })

    final_manifest["split_counts"] = class_summary

    # Overall validation
    all_train = {s["image_id"] for s in final_manifest["samples"] if s["split"] == "train"}
    all_val = {s["image_id"] for s in final_manifest["samples"] if s["split"] == "val"}
    all_test = {s["image_id"] for s in final_manifest["samples"] if s["split"] == "test"}

    assert all_train.isdisjoint(all_val)
    assert all_train.isdisjoint(all_test)
    assert all_val.isdisjoint(all_test)
    assert len(all_test & smoke_ids) == 0, "Contamination detected: smoke test images found in final test set!"
    assert len(all_val & smoke_ids) == 0, "Contamination detected: smoke test images found in final val set!"
    assert len(final_manifest["samples"]) == 7180

    print("\n========================================================")
    print("           FROZEN FINAL DATASET SPLIT COUNTS             ")
    print("========================================================")
    print(f"{'Class':<6} | {'Total':<6} | {'Train (70%)':<12} | {'Val (15%)':<10} | {'Test (15%)':<10}")
    print("-" * 56)
    total_tr, total_va, total_te = 0, 0, 0
    for cname, counts in class_summary.items():
        print(f"{cname:<6} | {counts['total']:<6} | {counts['train']:<12} | {counts['val']:<10} | {counts['test']:<10}")
        total_tr += counts['train']
        total_va += counts['val']
        total_te += counts['test']
    print("-" * 56)
    print(f"{'TOTAL':<6} | {7180:<6} | {total_tr:<12} | {total_va:<10} | {total_te:<10}")
    print(f"Percentage Breakdown: Train = {total_tr/7180*100:.2f}%, Val = {total_va/7180*100:.2f}%, Test = {total_te/7180*100:.2f}%")

    # Save frozen manifest and splits.json in data/CRC-VAL-HE-7K/
    manifest_path = data_dir / "frozen_final_split_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(final_manifest, f, indent=2)

    cache_path = data_dir / "splits.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(splits_cache_dict, f, indent=2)

    print(f"\nSaved frozen final manifest to: {manifest_path}")
    print(f"Saved splits cache to: {cache_path}")


if __name__ == "__main__":
    main()
