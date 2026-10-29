"""
Tests for CRCDataset and data pipeline augmentation behavior.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
from PIL import Image
import pytest
import torch

from src.dataset import CRCDataset, get_data_splits
from src.stain_shift import MacenkoStainDecomposer


def test_decomposer_initialized_for_train_stain_augmented(synthetic_he_patch, tmp_path):
    """Proves that transform_mode='train_stain_augmented' initializes a real decomposer."""
    img_path = tmp_path / "TUM-0001.png"
    Image.fromarray(synthetic_he_patch).save(img_path)

    ds = CRCDataset(
        file_paths=[img_path],
        labels=[0],
        transform_mode="train_stain_augmented",
        stain_profile="original",
    )
    assert ds.decomposer is not None
    assert isinstance(ds.decomposer, MacenkoStainDecomposer)


def test_decomposer_initialized_for_legacy_stain_augmented(synthetic_he_patch, tmp_path):
    """Proves that legacy alias 'stain_augmented' also initializes a real decomposer."""
    img_path = tmp_path / "TUM-0001.png"
    Image.fromarray(synthetic_he_patch).save(img_path)

    ds = CRCDataset(
        file_paths=[img_path],
        labels=[0],
        transform_mode="stain_augmented",
    )
    assert ds.decomposer is not None
    assert isinstance(ds.decomposer, MacenkoStainDecomposer)


def test_decomposer_none_for_standard_training(synthetic_he_patch, tmp_path):
    """Proves that standard training does not unnecessarily instantiate a decomposer."""
    img_path = tmp_path / "TUM-0001.png"
    Image.fromarray(synthetic_he_patch).save(img_path)

    ds = CRCDataset(
        file_paths=[img_path],
        labels=[0],
        transform_mode="train_standard",
    )
    assert ds.decomposer is None


def test_rejects_unsupported_transform_mode(synthetic_he_patch, tmp_path):
    """Proves that invalid transform modes fail loudly with ValueError."""
    img_path = tmp_path / "TUM-0001.png"
    Image.fromarray(synthetic_he_patch).save(img_path)

    with pytest.raises(ValueError, match="Unsupported transform_mode"):
        CRCDataset(
            file_paths=[img_path],
            labels=[0],
            transform_mode="non_existent_mode"
        )


def test_rejects_unsupported_stain_profile(synthetic_he_patch, tmp_path):
    """Proves that invalid stain profiles fail loudly with ValueError."""
    img_path = tmp_path / "TUM-0001.png"
    Image.fromarray(synthetic_he_patch).save(img_path)

    with pytest.raises(ValueError, match="Unknown stain profile"):
        CRCDataset(
            file_paths=[img_path],
            labels=[0],
            transform_mode="eval_shifted",
            stain_profile="invented_scanner_profile"
        )


def test_train_stain_augmented_invokes_perturbation(synthetic_he_patch, tmp_path):
    """Proves that stain perturbation branch is actually invoked during augmented training."""
    img_path = tmp_path / "TUM-0001.png"
    Image.fromarray(synthetic_he_patch).save(img_path)

    # Use a mock decomposer to definitively check that perturb is called
    ds = CRCDataset(
        file_paths=[img_path],
        labels=[0],
        transform_mode="train_stain_augmented",
    )
    mock_decomposer = MagicMock(spec=MacenkoStainDecomposer)
    mock_decomposer.perturb.return_value = synthetic_he_patch.copy()
    ds.decomposer = mock_decomposer

    # Set rng to trigger probability branch (< 0.60) and supply uniform values
    ds.rng = MagicMock()
    ds.rng.random.side_effect = [0.9, 0.9, 0.1]  # flips > 0.5 (skip), stain < 0.60 (run)
    ds.rng.choice.return_value = 0
    ds.rng.uniform.side_effect = [1.2, 0.9, 2.0]

    tensor, label, path = ds[0]
    assert mock_decomposer.perturb.called
    assert ds.transform_stats["attempts"] == 1
    assert ds.transform_stats["successes"] == 1


def test_unexpected_programming_errors_fail_loudly_when_fail_mode_raise(synthetic_he_patch, tmp_path):
    """Proves that unexpected programming defects are NOT silently caught."""
    img_path = tmp_path / "TUM-0001.png"
    Image.fromarray(synthetic_he_patch).save(img_path)

    ds = CRCDataset(
        file_paths=[img_path],
        labels=[0],
        transform_mode="train_stain_augmented",
        fail_mode="raise",
    )
    # Deliberately inject a decomposer that raises an unhandled error
    ds.decomposer = MagicMock()
    ds.decomposer.perturb.side_effect = TypeError("Unexpected programming bug")
    ds.rng.random = MagicMock(return_value=0.1)

    with pytest.raises(TypeError, match="Unexpected programming bug"):
        _ = ds[0]
