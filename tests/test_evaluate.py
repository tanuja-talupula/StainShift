"""
Tests for evaluate module: metrics, zero-division handling, and failure recording.
"""

from unittest.mock import MagicMock
import numpy as np
import pytest
import torch

from src.evaluate import evaluate_stain_profile
from src.models import CLASS_NAMES, get_model


def test_evaluate_stain_profile_with_mock_model(synthetic_he_patch, tmp_path):
    """Tests evaluation metrics calculation and transform failure tracking."""
    # Create 3 image files
    file_paths = []
    for i in range(3):
        p = tmp_path / f"img_{i}.png"
        from PIL import Image
        Image.fromarray(synthetic_he_patch).save(p)
        file_paths.append(str(p))

    labels = [0, 1, 2]
    model = get_model("mobilenet_v3_small", pretrained=False, num_classes=len(CLASS_NAMES))
    model.eval()

    res = evaluate_stain_profile(
        model=model,
        file_paths=file_paths,
        labels=labels,
        profile_name="original",
        batch_size=2,
        device="cpu",
    )

    assert "accuracy" in res
    assert "macro_f1" in res
    assert "classification_report" in res
    assert res["evaluated_count"] == 3
    assert res["transform_stats"]["failures"] == 0
    assert 0.0 <= res["accuracy"] <= 1.0
    assert 0.0 <= res["macro_f1"] <= 1.0


def test_missing_classes_in_evaluation_do_not_throw(synthetic_he_patch, tmp_path):
    """Proves that evaluations where only a subset of classes are present handle zero_division gracefully."""
    # All 2 samples have label 0 (other 8 classes are absent)
    file_paths = []
    for i in range(2):
        p = tmp_path / f"single_class_{i}.png"
        from PIL import Image
        Image.fromarray(synthetic_he_patch).save(p)
        file_paths.append(str(p))

    labels = [0, 0]
    model = get_model("mobilenet_v3_small", pretrained=False, num_classes=len(CLASS_NAMES))
    model.eval()

    res = evaluate_stain_profile(
        model=model,
        file_paths=file_paths,
        labels=labels,
        profile_name="original",
        batch_size=2,
        device="cpu",
    )

    # Classification report must contain entries for all classes with zero_division=0
    report = res["classification_report"]
    for cname in CLASS_NAMES:
        assert cname in report
        assert "f1-score" in report[cname]
