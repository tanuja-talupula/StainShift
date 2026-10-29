"""
Unit tests for Option B demonstration examples and prediction integrity.
"""

import json
import math
from pathlib import Path
import pytest

from src.models import CLASS_NAMES
from src.stain_shift import DISTINCT_STAIN_PROFILES


@pytest.fixture
def demo_manifest():
    manifest_p = Path("website/public/demo/demo_manifest.json")
    assert manifest_p.is_file(), f"Demo manifest not found at {manifest_p}"
    with open(manifest_p, "r", encoding="utf-8") as f:
        return json.load(f)


def test_demo_manifest_metadata(demo_manifest):
    meta = demo_manifest["metadata"]
    assert "First lexicographically sorted patch ID per class" in meta["selection_rule"]
    assert meta["mlflow_evaluation_run_id"] == "c76c59f4bd7c4fe39f2ed2135856845a"
    assert meta["frozen_split_manifest_sha256"] == "15ad014637fa207d79bd2b02b3adda6bf9ca22035d36cf9f296d04f6bdec0050"
    assert meta["total_patches_selected"] == 9
    assert meta["conditions_per_patch"] == 8
    assert meta["total_images_generated"] == 72


def test_demo_examples_class_coverage_and_conditions(demo_manifest):
    examples = demo_manifest["examples"]
    assert len(examples) == 9

    found_classes = [ex["tissue_class"] for ex in examples]
    assert found_classes == CLASS_NAMES

    for ex in examples:
        conds = ex["conditions"]
        assert len(conds) == 8
        for prof_name in DISTINCT_STAIN_PROFILES:
            assert prof_name in conds


def test_demo_prediction_probabilities_and_correctness(demo_manifest):
    """Verifies that probabilities normalize to 1.0, confidence is max probability, and is_correct is accurate."""
    for ex in demo_manifest["examples"]:
        true_cls = ex["tissue_class"]
        for cond_name, cdata in ex["conditions"].items():
            # Check image exists on disk
            img_rel = cdata["image_url"].lstrip("/")
            img_disk = Path("website/public") / img_rel
            assert img_disk.is_file(), f"Image file missing: {img_disk}"
            assert img_disk.stat().st_size > 1000, f"Image file is suspiciously small: {img_disk}"

            for m_key in ["baseline", "robust_stain_aug"]:
                m_pred = cdata[m_key]
                pred_cls = m_pred["predicted_class"]
                conf = m_pred["confidence"]
                is_correct = m_pred["is_correct"]
                probs = m_pred["probabilities"]

                assert len(probs) == 9
                prob_sum = sum(probs.values())
                assert math.isclose(prob_sum, 1.0, rel_tol=1e-3), f"Probabilities do not sum to 1.0: {prob_sum}"

                assert math.isclose(conf, probs[pred_cls], abs_tol=1e-4), "Confidence does not match predicted class probability"
                assert is_correct == (pred_cls == true_cls), f"is_correct flag mismatch for {ex['patch_id']} on {cond_name}"


def test_first_lexicographical_patch_selection():
    """Confirms patch IDs strictly follow the first sorted test split patch rule."""
    with open("data/CRC-VAL-HE-7K/splits.json", "r", encoding="utf-8") as f:
        splits = json.load(f)

    test_files = splits["test"]["files"]
    test_labels = splits["test"]["labels"]

    with open("website/public/demo/demo_manifest.json", "r", encoding="utf-8") as f:
        demo_manifest = json.load(f)

    for idx, cname in enumerate(CLASS_NAMES):
        expected_first = sorted([f for f, l in zip(test_files, test_labels) if l == idx])[0]
        expected_patch_id = Path(expected_first).stem

        actual_patch_id = demo_manifest["examples"][idx]["patch_id"]
        assert actual_patch_id == expected_patch_id, (
            f"Class {cname} selected patch {actual_patch_id}, expected first sorted {expected_patch_id}"
        )
