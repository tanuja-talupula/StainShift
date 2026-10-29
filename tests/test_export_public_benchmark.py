"""
Unit tests for public benchmark exporter and JSON schema validation.
"""

import json
from pathlib import Path
import pytest

from scripts.export_public_benchmark import (
    validate_public_export,
    DISTINCT_CONDITIONS,
    LEGACY_ALIASES,
    CLASS_NAMES,
)


@pytest.fixture
def public_export_data():
    json_path = Path("public/data/stainshift_results.json")
    assert json_path.is_file(), "Exported public benchmark JSON does not exist"
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_public_export_passes_validation(public_export_data):
    """Verifies that the generated public JSON passes all schema and value checks."""
    validate_public_export(public_export_data)


def test_public_export_metadata_and_provenance(public_export_data):
    """Verifies metadata provenance fields."""
    bm = public_export_data["benchmark_metadata"]
    assert bm["mlflow_run_id"] == "c76c59f4bd7c4fe39f2ed2135856845a"
    assert bm["run_type"] == "full_experiment"
    assert len(bm["git_commit"]) == 40

    dm = public_export_data["dataset_metadata"]
    assert dm["total_images"] == 7180
    assert dm["train_images"] == 5026
    assert dm["val_images"] == 1077
    assert dm["held_out_test_images"] == 1077
    assert dm["split_manifest_sha256"] == "15ad014637fa207d79bd2b02b3adda6bf9ca22035d36cf9f296d04f6bdec0050"


def test_distinct_conditions_and_no_legacy_aliases(public_export_data):
    """Ensures exactly 8 distinct conditions and 0 legacy aliases."""
    conds = public_export_data["conditions_evaluated"]
    assert len(conds) == 8
    assert conds == DISTINCT_CONDITIONS
    for alias in LEGACY_ALIASES:
        assert alias not in conds


def test_results_metrics_sanity(public_export_data):
    """Ensures metrics are finite, bounded, and evaluation counts match 1077."""
    res = public_export_data["results"]
    for mname in ["baseline", "robust_stain_aug"]:
        assert mname in res
        for cname in DISTINCT_CONDITIONS:
            entry = res[mname][cname]
            assert 0.0 <= entry["accuracy"] <= 100.0
            assert 0.0 <= entry["macro_f1"] <= 1.0
            assert entry["evaluated_count"] == 1077
            assert entry["transform_failures"] == 0
            assert len(entry["confusion_matrix"]) == 9
            assert len(entry["per_class"]) == 9

            # Check original reference
            if cname == "original":
                assert entry["accuracy_drop_pct"] == 0.0


def test_latency_structure_and_disclaimer(public_export_data):
    """Ensures latency results contain clear device, timing boundary, and disclaimers."""
    lat = public_export_data["latency_benchmarks"]
    assert "Apple Silicon MPS" in lat["disclaimer"]
    assert "must not be conflated with website or HTTP API network latency" in lat["disclaimer"]

    for prof_key in ["baseline_mps", "robust_stain_aug_mps"]:
        prof = lat["profiles"][prof_key]
        assert prof["device"] == "mps"
        fwd = prof["model_forward_batch1"]
        assert fwd["units"] == "milliseconds"
        assert fwd["mean_ms"] > 0.0
        assert fwd["p95_ms"] >= fwd["median_ms"]


def test_no_private_paths_or_secrets(public_export_data):
    """Ensures no developer paths or secrets leak into public file."""
    serialized = json.dumps(public_export_data)
    for forbidden in ["/Users/", "/home/", "\\Users\\", "password", "token", "secret"]:
        assert forbidden.lower() not in serialized.lower()


def test_validate_public_export_catches_invalid_data(public_export_data):
    """Ensures validate_public_export rejects corrupted or incomplete data."""
    import copy

    # Test missing key
    corrupted = copy.deepcopy(public_export_data)
    del corrupted["dataset_metadata"]
    with pytest.raises(ValueError, match="Missing required top-level key"):
        validate_public_export(corrupted)

    # Test legacy alias inclusion
    corrupted = copy.deepcopy(public_export_data)
    corrupted["conditions_evaluated"].append("scanner_warm_shift")
    with pytest.raises(ValueError):
        validate_public_export(corrupted)

    # Test non-finite value
    corrupted = copy.deepcopy(public_export_data)
    corrupted["results"]["baseline"]["original"]["accuracy"] = float("nan")
    with pytest.raises(ValueError, match="Invalid accuracy"):
        validate_public_export(corrupted)
