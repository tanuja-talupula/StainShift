"""
Unit and integration tests for StainShift FastAPI Inference API.
Validates endpoints, checkpoint loading, image format support, ZIP extraction,
stain transformations, and mathematical parity with direct PyTorch inference.
"""

from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path
from typing import List
import zipfile

from fastapi import HTTPException, UploadFile
import numpy as np
from PIL import Image
import pytest
import torch

from api.main import (
    app,
    engine,
    get_health,
    get_models,
    predict,
    predict_batch,
)
from src.models import CLASS_NAMES, load_checkpoint


@pytest.fixture(scope="module")
def sample_png_bytes() -> bytes:
    """Creates a synthetic 224x224 RGB pathology-like image."""
    img = Image.new("RGB", (224, 224), color=(180, 100, 160))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def sample_jpg_bytes() -> bytes:
    img = Image.new("RGB", (224, 224), color=(200, 120, 180))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def sample_tiff_bytes() -> bytes:
    img = Image.new("RGB", (224, 224), color=(160, 90, 150))
    buf = io.BytesIO()
    img.save(buf, format="TIFF")
    return buf.getvalue()


@pytest.fixture(scope="module")
def sample_zip_bytes(sample_png_bytes: bytes, sample_jpg_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test_patch_1.png", sample_png_bytes)
        zf.writestr("test_patch_2.jpg", sample_jpg_bytes)
    return buf.getvalue()


def test_health_endpoint() -> None:
    data = get_health()
    assert data.status == "healthy"
    assert data.models_available["baseline"] is True
    assert data.models_available["robust_stain_aug"] is True
    assert "png" in data.supported_formats
    assert "original" in data.supported_conditions
    assert len(data.models) == 2


def test_models_endpoint() -> None:
    data = get_models()
    assert len(data) == 2
    model_ids = [m.id for m in data]
    assert "baseline" in model_ids
    assert "robust_stain_aug" in model_ids
    for m in data:
        assert len(m.checkpoint_sha256) == 64
        assert m.classes == CLASS_NAMES


def test_predict_single_image(sample_png_bytes: bytes) -> None:
    uf = UploadFile(file=io.BytesIO(sample_png_bytes), filename="patch.png")
    data = asyncio.run(predict(
        files=[uf],
        model_id="robust_stain_aug",
        condition="original",
        intensity=1.0,
    ))
    assert data.status == "success"
    assert data.summary.successful_files == 1
    assert len(data.results) == 1

    res = data.results[0]
    assert res.filename == "patch.png"
    assert res.status == "success"
    assert res.original_thumbnail_b64.startswith("data:image/png;base64,")

    pred = res.predictions["robust_stain_aug"]
    assert pred.predicted_class in CLASS_NAMES
    assert 0.0 <= pred.confidence <= 1.0
    assert len(pred.probabilities) == 9

    prob_sum = sum(pred.probabilities.values())
    assert abs(prob_sum - 1.0) < 0.01


def test_predict_comparison_mode(sample_jpg_bytes: bytes) -> None:
    uf = UploadFile(file=io.BytesIO(sample_jpg_bytes), filename="slide.jpg")
    data = asyncio.run(predict(
        files=[uf],
        model_id="compare",
        condition="heavy_hematoxylin",
        intensity=1.2,
    ))
    assert data.status == "success"
    res = data.results[0]
    assert "baseline" in res.predictions
    assert "robust_stain_aug" in res.predictions
    assert isinstance(res.agreement, bool)
    assert res.condition_applied == "heavy_hematoxylin"
    assert res.intensity_applied == 1.2


def test_predict_tiff_format(sample_tiff_bytes: bytes) -> None:
    uf = UploadFile(file=io.BytesIO(sample_tiff_bytes), filename="tissue.tif")
    data = asyncio.run(predict(
        files=[uf],
        model_id="baseline",
        condition="original",
    ))
    assert data.status == "success"
    assert data.results[0].status == "success"


def test_predict_zip_upload(sample_zip_bytes: bytes) -> None:
    uf = UploadFile(file=io.BytesIO(sample_zip_bytes), filename="patches.zip")
    data = asyncio.run(predict(
        files=[uf],
        model_id="robust_stain_aug",
        condition="original",
    ))
    assert data.status == "success"
    assert data.summary.total_files == 2
    assert data.summary.successful_files == 2
    filenames = [r.filename for r in data.results]
    assert "test_patch_1.png" in filenames
    assert "test_patch_2.jpg" in filenames


def test_reject_unsupported_format() -> None:
    uf = UploadFile(file=io.BytesIO(b"Hello world text file"), filename="notes.txt")
    data = asyncio.run(predict(
        files=[uf],
        model_id="baseline",
    ))
    assert data.status == "error"
    assert data.results[0].status == "error"
    assert "Unsupported format" in data.results[0].error_message


def test_reject_corrupted_image() -> None:
    uf = UploadFile(file=io.BytesIO(b"\x89PNG\r\n\x1a\nCorruptedHeader"), filename="broken.png")
    data = asyncio.run(predict(
        files=[uf],
        model_id="baseline",
    ))
    assert data.status == "error"
    assert data.results[0].status == "error"
    assert "Failed to parse image" in data.results[0].error_message


def test_direct_inference_parity() -> None:
    """Verifies that API inference exactly matches direct PyTorch forward pass."""
    held_out_patch = Path("data/CRC-VAL-HE-7K/TUM/TUM-TCGA-ACRLPPQE.tif")
    if not held_out_patch.is_file():
        pytest.skip("Held-out test patch not available on disk.")

    raw_bytes = held_out_patch.read_bytes()

    # 1. API prediction
    uf = UploadFile(file=io.BytesIO(raw_bytes), filename="TUM-TCGA-ACRLPPQE.tif")
    api_res = asyncio.run(predict(
        files=[uf],
        model_id="robust_stain_aug",
        condition="original",
    ))

    api_pred = api_res.results[0].predictions["robust_stain_aug"]

    # 2. Direct model execution
    direct_model, _ = load_checkpoint(
        "models/full_benchmark_20261029_1838/robust_stain_aug.pth",
        device="cpu"
    )
    direct_model.eval()

    with Image.open(held_out_patch) as img:
        rgb_224 = img.convert("RGB").resize((224, 224), Image.Resampling.BILINEAR)

    tensor = engine.tensor_transform(rgb_224).unsqueeze(0)
    with torch.no_grad():
        direct_logits = direct_model(tensor)
        direct_probs = torch.softmax(direct_logits, dim=1)[0].numpy()

    direct_class_idx = int(np.argmax(direct_probs))
    direct_class = CLASS_NAMES[direct_class_idx]
    direct_conf = float(direct_probs[direct_class_idx])

    assert api_pred.predicted_class == direct_class
    assert abs(api_pred.confidence - direct_conf) < 1e-4

    for i, c in enumerate(CLASS_NAMES):
        assert abs(api_pred.probabilities[c] - float(direct_probs[i])) < 1e-4


def test_invalid_parameters_raise_http_exception() -> None:
    uf = UploadFile(file=io.BytesIO(b"abc"), filename="patch.png")
    with pytest.raises(HTTPException) as exc1:
        asyncio.run(predict(files=[uf], model_id="invalid_model"))
    assert exc1.value.status_code == 400

    with pytest.raises(HTTPException) as exc2:
        asyncio.run(predict(files=[uf], condition="invalid_condition"))
    assert exc2.value.status_code == 400

    with pytest.raises(HTTPException) as exc3:
        asyncio.run(predict(files=[uf], intensity=99.0))
    assert exc3.value.status_code == 400
