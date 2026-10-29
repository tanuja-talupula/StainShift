"""
Tests for dataset splitting determinism, disjointness, and cache behavior.
"""

from pathlib import Path
import pytest

from src.dataset import get_data_splits


def test_splits_determinism_and_reproducibility(synthetic_dataset_dir):
    """Proves that identical splits are produced across repeated calls with the same seed."""
    tr1, val1, te1 = get_data_splits(synthetic_dataset_dir, seed=42)
    tr2, val2, te2 = get_data_splits(synthetic_dataset_dir, seed=42)

    assert tr1["files"] == tr2["files"]
    assert val1["files"] == val2["files"]
    assert te1["files"] == te2["files"]


def test_splits_sample_disjointness(synthetic_dataset_dir):
    """Proves that train, val, and test splits are strictly disjoint (0 sample overlap)."""
    tr, val, te = get_data_splits(synthetic_dataset_dir, seed=42)

    s_tr = set(tr["files"])
    s_val = set(val["files"])
    s_te = set(te["files"])

    assert len(s_tr & s_val) == 0
    assert len(s_tr & s_te) == 0
    assert len(s_val & s_te) == 0


def test_splits_cache_roundtrip(synthetic_dataset_dir, tmp_path):
    """Tests saving and reloading splits from a cache file."""
    cache_file = tmp_path / "splits.json"
    tr1, val1, te1 = get_data_splits(synthetic_dataset_dir, splits_cache=cache_file, seed=42)
    assert cache_file.is_file()

    tr2, val2, te2 = get_data_splits(synthetic_dataset_dir, splits_cache=cache_file, seed=42)
    assert tr1["files"] == tr2["files"]
    assert val1["files"] == val2["files"]
    assert te1["files"] == te2["files"]
