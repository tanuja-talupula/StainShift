"""
Tests for latency and throughput benchmarking module (src/benchmark.py).
Verifies:
- Statistical calculations (mean, std, median, p95).
- Model-forward timing without brittle absolute speed limits.
- Preprocessing-inclusive timing with stain transformation.
- Batched throughput calculations.
"""

from pathlib import Path
import numpy as np
import pytest
from PIL import Image
import torch
import torch.nn as nn

from src.benchmark import (
    benchmark_forward_latency,
    benchmark_preprocessing_inclusive_latency,
    benchmark_batch_throughput,
    compute_statistics,
    run_full_latency_benchmark,
)


class DummyBenchmarkModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(3, 8, kernel_size=3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(8, 9)

    def forward(self, x):
        return self.fc(self.pool(self.conv(x)).flatten(1))


def test_compute_statistics():
    data = [10.0, 20.0, 30.0, 40.0, 50.0]
    stats = compute_statistics(data)
    assert stats["mean_ms"] == 30.0
    assert stats["median_ms"] == 30.0
    assert stats["min_ms"] == 10.0
    assert stats["max_ms"] == 50.0
    assert stats["p95_ms"] >= 40.0
    assert stats["std_ms"] > 0.0


def test_benchmark_forward_latency_cpu():
    model = DummyBenchmarkModel()
    res = benchmark_forward_latency(model, device="cpu", batch_size=1, warm_up=2, repetitions=5)
    assert res["timing_boundary"] == "model_forward_only"
    assert res["batch_size"] == 1
    stats = res["statistics"]
    assert stats["mean_ms"] > 0.0
    assert stats["p95_ms"] >= stats["median_ms"]
    assert stats["max_ms"] >= stats["min_ms"]


def test_benchmark_preprocessing_inclusive_latency(tmp_path, synthetic_he_patch):
    img_path = tmp_path / "patch.tif"
    Image.fromarray(synthetic_he_patch).save(img_path)

    model = DummyBenchmarkModel()
    res = benchmark_preprocessing_inclusive_latency(
        model, [img_path], stain_profile="original", device="cpu", warm_up=2, repetitions=4
    )
    assert res["timing_boundary"] == "preprocessing_inclusive_local_inference"
    assert res["failures_encountered"] == 0
    stats = res["statistics"]
    assert stats["mean_ms"] > 0.0


def test_benchmark_batch_throughput():
    model = DummyBenchmarkModel()
    res = benchmark_batch_throughput(model, device="cpu", batch_size=4, warm_up=2, repetitions=4)
    assert res["timing_boundary"] == "batched_model_throughput"
    assert res["batch_size"] == 4
    assert res["throughput_samples_per_second"] > 0.0
    assert "ms_per_batch" in res


def test_run_full_latency_benchmark(tmp_path, synthetic_he_patch):
    img_path = tmp_path / "patch.tif"
    Image.fromarray(synthetic_he_patch).save(img_path)

    model = DummyBenchmarkModel()
    res = run_full_latency_benchmark(
        model, [img_path], device="cpu", batch_size=4, warm_up=2, repetitions=3, model_name="dummy_test"
    )
    assert res["model_name"] == "dummy_test"
    assert "environment" in res
    assert "model_forward_batch1" in res
    assert "preprocessing_inclusive_original" in res
    assert "preprocessing_inclusive_heavy_hematoxylin" in res
    assert "batched_throughput" in res
