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

from src.dataset import (
    CLASS_NAMES,
    CRCDataset,
    get_data_splits,
    scan_dataset_files,
)
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


def test_scan_dataset_files_nested_tiff(tmp_path, synthetic_he_patch):
    """Regression test: verifies scanning nested class directories containing .tif and .tiff files."""
    for cname in ["ADI", "TUM", "STR"]:
        cdir = tmp_path / cname
        cdir.mkdir(parents=True)
        img = Image.fromarray(synthetic_he_patch)
        img.save(cdir / "patch_01.tif")
        img.save(cdir / "patch_02.tiff")

    scanned = scan_dataset_files(tmp_path)
    assert len(scanned["ADI"]) == 2
    assert len(scanned["TUM"]) == 2
    assert len(scanned["STR"]) == 2
    assert len(scanned["BACK"]) == 0
    # Verify deterministic relative POSIX path sorting
    assert scanned["ADI"][0].name == "patch_01.tif"
    assert scanned["ADI"][1].name == "patch_02.tiff"


def test_scan_dataset_files_flat_png(tmp_path, synthetic_he_patch):
    """Regression test: verifies scanning flat directory with <CLASS>-<ID>.png naming."""
    img = Image.fromarray(synthetic_he_patch)
    for cname in ["DEB", "LYM"]:
        for i in range(3):
            img.save(tmp_path / f"{cname}-{i:04d}.png")

    scanned = scan_dataset_files(tmp_path)
    assert len(scanned["DEB"]) == 3
    assert len(scanned["LYM"]) == 3


def test_scan_dataset_files_wrapped_nested_archive(tmp_path, synthetic_he_patch):
    """Regression test: verifies scanning archive wrapper directory (e.g. data/CRC-VAL-HE-7K/<CLASS>/*.tif)."""
    wrapped_dir = tmp_path / "CRC-VAL-HE-7K" / "MUC"
    wrapped_dir.mkdir(parents=True)
    img = Image.fromarray(synthetic_he_patch)
    img.save(wrapped_dir / "muc_sample.tif")

    scanned = scan_dataset_files(tmp_path)
    assert len(scanned["MUC"]) == 1
    assert scanned["MUC"][0].name == "muc_sample.tif"


def test_scan_dataset_files_empty_raises_filenotfound(tmp_path):
    """Regression test: empty directory raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="No valid histology image files"):
        scan_dataset_files(tmp_path)


def test_scan_dataset_files_unrecognized_classes_raises_valueerror(tmp_path, synthetic_he_patch):
    """Regression test: image files with invalid or non-CRC class names raise ValueError."""
    invalid_dir = tmp_path / "UNKNOWN_CLASS"
    invalid_dir.mkdir(parents=True)
    img = Image.fromarray(synthetic_he_patch)
    img.save(invalid_dir / "test.tif")

    with pytest.raises(ValueError, match="none matched expected class names"):
        scan_dataset_files(tmp_path)


def test_dataset_rgba_tiff_conversion_and_unsupported_mode_rejection(tmp_path):
    """Regression test: verifies RGBA is converted to 3-channel RGB and unsupported modes (16-bit, palette) are rejected."""
    rgba_path = tmp_path / "TUM_rgba.tif"
    i16_path = tmp_path / "TUM_16bit.tif"
    palette_path = tmp_path / "TUM_palette.png"

    # Create 4-channel RGBA image (supported via alpha drop to RGB)
    rgba_data = np.full((100, 100, 4), 200, dtype=np.uint8)
    Image.fromarray(rgba_data, mode="RGBA").save(rgba_path)

    # Create 16-bit integer image (unsupported: must be rejected)
    i16_data = np.full((100, 100), 30000, dtype=np.uint16)
    Image.fromarray(i16_data).save(i16_path)

    # Create palette image (unsupported: must be rejected)
    palette_img = Image.fromarray(np.full((100, 100), 1, dtype=np.uint8), mode="P")
    palette_img.save(palette_path)

    # Verify RGBA loads properly into 3-channel RGB tensor
    ds_valid = CRCDataset(
        file_paths=[rgba_path],
        labels=[0],
        transform_mode="eval_standard",
    )
    tensor_rgba, _, _ = ds_valid[0]
    assert tensor_rgba.shape == (3, 100, 100)

    # Verify 16-bit image fails loudly
    ds_16bit = CRCDataset(
        file_paths=[i16_path],
        labels=[0],
        transform_mode="eval_standard",
    )
    with pytest.raises(RuntimeError, match="Unsupported image mode"):
        _ = ds_16bit[0]

    # Verify palette image fails loudly
    ds_pal = CRCDataset(
        file_paths=[palette_path],
        labels=[0],
        transform_mode="eval_standard",
    )
    with pytest.raises(RuntimeError, match="Unsupported image mode"):
        _ = ds_pal[0]


def test_get_data_splits_nested_tiff(tmp_path, synthetic_he_patch):
    """Regression test: verifies complete split generation on nested TIFF folder layout."""
    img = Image.fromarray(synthetic_he_patch)
    for cname in CLASS_NAMES:
        cdir = tmp_path / cname
        cdir.mkdir(parents=True)
        for i in range(10):
            img.save(cdir / f"sample_{i:02d}.tif")

    train_split, val_split, test_split = get_data_splits(tmp_path, seed=42)
    assert len(train_split["files"]) > 0
    assert len(val_split["files"]) > 0
    assert len(test_split["files"]) > 0
    # Check disjointness
    train_set = set(train_split["files"])
    val_set = set(val_split["files"])
    test_set = set(test_split["files"])
    assert train_set.isdisjoint(val_set)
    assert train_set.isdisjoint(test_set)
    assert val_set.isdisjoint(test_set)

