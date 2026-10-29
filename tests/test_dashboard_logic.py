"""
Tests for dashboard inference and transition interpretation logic.
"""

import numpy as np
import pytest
import torch

from app import discover_and_load_models, predict, preprocess_tensor
from src.models import CLASS_NAMES, get_model, save_checkpoint


def test_discover_and_load_models_ignores_empty(tmp_path, monkeypatch):
    """Proves that when models/ has no checkpoints, discover_and_load_models returns empty dict without inventing weights."""
    empty_dir = tmp_path / "models"
    empty_dir.mkdir()
    monkeypatch.setattr("app.BASE_DIR", tmp_path)

    available = discover_and_load_models()
    assert len(available) == 0


def test_predict_function_probabilities(synthetic_he_patch):
    """Tests that predict produces valid probability distribution summing to ~1.0."""
    model = get_model("mobilenet_v3_small", pretrained=False, num_classes=len(CLASS_NAMES))
    model.eval()

    pred_idx, probs = predict(model, synthetic_he_patch)
    assert 0 <= pred_idx < len(CLASS_NAMES)
    assert probs.shape == (len(CLASS_NAMES),)
    assert np.isclose(np.sum(probs), 1.0, atol=1e-5)
    assert np.all(probs >= 0.0)
