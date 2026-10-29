"""
StainShift Latency and Throughput Benchmarking Module.
Provides high-resolution, device-synchronized latency profiling distinguishing:
1. Model-forward latency with batch_size=1.
2. Preprocessing-inclusive inference latency with batch_size=1.
3. Batched throughput (samples/second and ms/batch).

Strictly adheres to evaluation boundaries:
- Evaluates models in eval() mode with torch.inference_mode().
- Distinguishes device synchronization (CUDA, MPS, CPU).
- Does not conflate local timing with network/web API latency.
- Excludes training, checkpoint loading, downloads, or MLflow overhead from measured timing loops.
"""

from __future__ import annotations

import logging
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as T

from .dataset import IMAGENET_MEAN, IMAGENET_STD
from .stain_shift import STAIN_PROFILES, apply_stain_profile, MacenkoStainDecomposer

logger = logging.getLogger(__name__)


def sync_device(device: torch.device) -> None:
    """Synchronizes hardware queue for accurate asynchronous timing."""
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    elif device.type == "mps":
        if hasattr(torch, "mps") and hasattr(torch.mps, "synchronize"):
            torch.mps.synchronize()
    # CPU requires no device synchronization


def compute_statistics(latencies_ms: List[float]) -> Dict[str, float]:
    """Computes standard summary statistics in milliseconds."""
    arr = np.array(latencies_ms, dtype=np.float64)
    return {
        "mean_ms": round(float(np.mean(arr)), 4),
        "std_ms": round(float(np.std(arr)), 4),
        "median_ms": round(float(np.median(arr)), 4),
        "p95_ms": round(float(np.percentile(arr, 95)), 4),
        "min_ms": round(float(np.min(arr)), 4),
        "max_ms": round(float(np.max(arr)), 4),
    }


def get_environment_metadata(device: str) -> Dict[str, Any]:
    """Captures environment and hardware configuration."""
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "torchvision_version": torchvision.__version__,
        "device": device,
        "mps_available": torch.backends.mps.is_available() if hasattr(torch.backends, "mps") else False,
        "cuda_available": torch.cuda.is_available(),
    }


def benchmark_forward_latency(
    model: nn.Module,
    device: str = "cpu",
    batch_size: int = 1,
    image_size: Tuple[int, int] = (224, 224),
    warm_up: int = 10,
    repetitions: int = 50,
) -> Dict[str, Any]:
    """
    Measures pure model-forward latency for batch_size=1 (or specified batch).
    Timing boundary:
    - Tensor is PRE-LOADED on the target device.
    - Measures ONLY model forward execution and hardware synchronization.
    - Excludes disk I/O, PIL decoding, deconvolution, and tensor transfers.
    """
    dev = torch.device(device)
    model.eval()
    model.to(dev)

    # Pre-allocate input tensor on target device
    dummy_input = torch.randn(batch_size, 3, image_size[0], image_size[1], dtype=torch.float32, device=dev)

    # Warm-up phase
    with torch.inference_mode():
        for _ in range(warm_up):
            _ = model(dummy_input)
            sync_device(dev)

    latencies_ms: List[float] = []
    with torch.inference_mode():
        for _ in range(repetitions):
            sync_device(dev)
            t0 = time.perf_counter_ns()
            _ = model(dummy_input)
            sync_device(dev)
            t1 = time.perf_counter_ns()
            latencies_ms.append((t1 - t0) / 1e6)

    stats = compute_statistics(latencies_ms)
    return {
        "timing_boundary": "model_forward_only",
        "boundary_description": "Pure model forward pass on pre-loaded device tensor with hardware sync",
        "batch_size": batch_size,
        "image_size": list(image_size),
        "warm_up_calls": warm_up,
        "timed_calls": repetitions,
        "statistics": stats,
    }


def benchmark_preprocessing_inclusive_latency(
    model: nn.Module,
    image_paths: List[Union[str, Path]],
    stain_profile: str = "original",
    device: str = "cpu",
    warm_up: int = 5,
    repetitions: int = 20,
) -> Dict[str, Any]:
    """
    Measures complete end-to-end local inference latency for a single image (batch_size=1).
    Timing boundary:
    - Includes: Disk file read, PIL RGB decoding, stain perturbation (if non-original),
      tensor conversion, normalization, device transfer, forward pass, and hardware sync.
    - Excludes: Checkpoint loading, model instantiation, training loops, MLflow logging.
    """
    if not image_paths:
        raise ValueError("Must provide at least one image path for preprocessing latency measurement.")

    dev = torch.device(device)
    model.eval()
    model.to(dev)

    tensor_transform = T.Compose([
        T.ToTensor(),
        T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
    ])
    decomposer = MacenkoStainDecomposer() if stain_profile != "original" else None

    # Cycle through provided images
    paths_cycle = [Path(p) for p in image_paths]
    total_imgs = len(paths_cycle)

    failures = 0
    transform_exceptions = []

    # Warm-up phase
    with torch.inference_mode():
        for i in range(warm_up):
            p = paths_cycle[i % total_imgs]
            with Image.open(p) as img:
                rgb_arr = np.array(img.convert("RGB"))
            if stain_profile != "original":
                rgb_arr = apply_stain_profile(rgb_arr, profile_name=stain_profile)
            inp = tensor_transform(Image.fromarray(rgb_arr)).unsqueeze(0).to(dev)
            _ = model(inp)
            sync_device(dev)

    latencies_ms: List[float] = []
    with torch.inference_mode():
        for i in range(repetitions):
            p = paths_cycle[i % total_imgs]
            sync_device(dev)
            t0 = time.perf_counter_ns()

            try:
                with Image.open(p) as img:
                    rgb_arr = np.array(img.convert("RGB"))

                if stain_profile != "original":
                    rgb_arr = apply_stain_profile(rgb_arr, profile_name=stain_profile)

                inp = tensor_transform(Image.fromarray(rgb_arr)).unsqueeze(0).to(dev)
                _ = model(inp)
                sync_device(dev)
                t1 = time.perf_counter_ns()
                latencies_ms.append((t1 - t0) / 1e6)
            except Exception as err:
                failures += 1
                transform_exceptions.append(str(err))

    stats = compute_statistics(latencies_ms) if latencies_ms else {}
    return {
        "timing_boundary": "preprocessing_inclusive_local_inference",
        "boundary_description": "PIL file read + optical density stain shift + tensor transform + host-to-device transfer + model forward + device sync",
        "stain_profile": stain_profile,
        "batch_size": 1,
        "unique_images_tested": total_imgs,
        "warm_up_calls": warm_up,
        "timed_calls": repetitions,
        "failures_encountered": failures,
        "failure_reasons": transform_exceptions[:5],
        "statistics": stats,
    }


def benchmark_batch_throughput(
    model: nn.Module,
    device: str = "cpu",
    batch_size: int = 16,
    image_size: Tuple[int, int] = (224, 224),
    warm_up: int = 5,
    repetitions: int = 20,
) -> Dict[str, Any]:
    """
    Measures batched inference throughput on pre-loaded device tensors.
    Reports:
    - ms_per_batch statistics (mean, median, p95).
    - throughput in samples_per_second.
    """
    dev = torch.device(device)
    model.eval()
    model.to(dev)

    dummy_batch = torch.randn(batch_size, 3, image_size[0], image_size[1], dtype=torch.float32, device=dev)

    # Warm-up phase
    with torch.inference_mode():
        for _ in range(warm_up):
            _ = model(dummy_batch)
            sync_device(dev)

    batch_latencies_ms: List[float] = []
    with torch.inference_mode():
        for _ in range(repetitions):
            sync_device(dev)
            t0 = time.perf_counter_ns()
            _ = model(dummy_batch)
            sync_device(dev)
            t1 = time.perf_counter_ns()
            batch_latencies_ms.append((t1 - t0) / 1e6)

    stats = compute_statistics(batch_latencies_ms)
    mean_batch_sec = stats["mean_ms"] / 1000.0
    samples_per_sec = round(float(batch_size / mean_batch_sec), 2) if mean_batch_sec > 0 else 0.0

    return {
        "timing_boundary": "batched_model_throughput",
        "batch_size": batch_size,
        "image_size": list(image_size),
        "warm_up_calls": warm_up,
        "timed_calls": repetitions,
        "ms_per_batch": stats,
        "throughput_samples_per_second": samples_per_sec,
    }


def run_full_latency_benchmark(
    model: nn.Module,
    sample_image_paths: List[Union[str, Path]],
    device: str = "cpu",
    batch_size: int = 16,
    warm_up: int = 5,
    repetitions: int = 20,
    model_name: str = "model",
) -> Dict[str, Any]:
    """
    Runs comprehensive benchmark suite across all three levels:
    1. Model forward latency (batch_size=1)
    2. Preprocessing-inclusive latency (batch_size=1)
    3. Batched throughput
    """
    metadata = get_environment_metadata(device)
    forward_res = benchmark_forward_latency(model, device=device, batch_size=1, warm_up=warm_up, repetitions=repetitions)
    preproc_orig_res = benchmark_preprocessing_inclusive_latency(
        model, sample_image_paths, stain_profile="original", device=device, warm_up=warm_up, repetitions=repetitions
    )
    preproc_heavy_h_res = benchmark_preprocessing_inclusive_latency(
        model, sample_image_paths, stain_profile="heavy_hematoxylin", device=device, warm_up=warm_up, repetitions=repetitions
    )
    throughput_res = benchmark_batch_throughput(
        model, device=device, batch_size=batch_size, warm_up=warm_up, repetitions=repetitions
    )

    return {
        "model_name": model_name,
        "environment": metadata,
        "model_forward_batch1": forward_res,
        "preprocessing_inclusive_original": preproc_orig_res,
        "preprocessing_inclusive_heavy_hematoxylin": preproc_heavy_h_res,
        "batched_throughput": throughput_res,
    }
