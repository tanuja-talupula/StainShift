"""
StainShift FastAPI Inference Service.
Provides REST endpoints for biomedical histopathology image classification,
stain shift simulations, model comparison, and batch predictions.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.inference import (
    MAX_BATCH_FILES,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_ARCHIVE_EXTENSIONS,
    InferenceEngine,
)
from api.schemas import (
    BatchSummary,
    HealthResponse,
    ImageInferenceResult,
    ModelInfo,
    PredictResponse,
)
from src.stain_shift import DISTINCT_STAIN_PROFILES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("stainshift.api")

# Models directory can be overridden via env var
MODELS_DIR = os.getenv("STAINSHIFT_MODELS_DIR", "models/full_benchmark_20261029_1838")
DEVICE = os.getenv("STAINSHIFT_DEVICE", None)

# Initialize engine on startup
engine = InferenceEngine(models_dir=MODELS_DIR, device=DEVICE)

app = FastAPI(
    title="StainShift AI Inference API",
    description="Physics-informed histopathology stain robustness inference engine",
    version="1.0.0",
)

# Configure CORS
allowed_origins_env = os.getenv("ALLOW_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if "*" not in allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Returns backend status, device, and model availability."""
    available_models = engine.get_available_models()
    models_dict = {
        m["id"]: True for m in available_models
    }
    # Ensure both models are checked
    if "baseline" not in models_dict:
        models_dict["baseline"] = False
    if "robust_stain_aug" not in models_dict:
        models_dict["robust_stain_aug"] = False

    is_healthy = any(models_dict.values())

    return HealthResponse(
        status="healthy" if is_healthy else "degraded",
        version="1.0.0",
        device=engine.device_str,
        models_available=models_dict,
        models=[ModelInfo(**m) for m in available_models],
        supported_formats=sorted(list({ext.lstrip(".") for ext in (SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_ARCHIVE_EXTENSIONS)})),
        supported_conditions=DISTINCT_STAIN_PROFILES,
    )


@app.get("/models", response_model=List[ModelInfo])
def get_models() -> List[ModelInfo]:
    """Returns available trained models and their verified provenance."""
    return [ModelInfo(**m) for m in engine.get_available_models()]


@app.post("/predict", response_model=PredictResponse)
async def predict(
    files: List[UploadFile] = File(..., description="One or more image files or a ZIP archive"),
    model_id: str = Form("robust_stain_aug", description="'baseline', 'robust_stain_aug', or 'compare'"),
    condition: str = Form("original", description="Stain shift condition"),
    intensity: float = Form(1.0, description="Perturbation intensity scaling factor (0.0 to 2.0)"),
) -> PredictResponse:
    """
    Accepts images or ZIP archive, applies requested stain condition,
    and runs genuine model inference using trained checkpoints.
    """
    # Unwrap FastAPI Form defaults if function is called directly in tests
    if hasattr(model_id, "default"):
        model_id = model_id.default
    if hasattr(condition, "default"):
        condition = condition.default
    if hasattr(intensity, "default"):
        intensity = intensity.default

    model_id = str(model_id)
    condition = str(condition)
    try:
        intensity = float(intensity)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid intensity value '{intensity}'. Must be a float.")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided for prediction.")

    if model_id not in ("baseline", "robust_stain_aug", "compare", "both"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model_id '{model_id}'. Must be 'baseline', 'robust_stain_aug', or 'compare'."
        )

    if condition not in DISTINCT_STAIN_PROFILES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid condition '{condition}'. Supported: {DISTINCT_STAIN_PROFILES}"
        )

    if intensity < 0.0 or intensity > 2.5:
        raise HTTPException(
            status_code=400,
            detail=f"Intensity must be between 0.0 and 2.5 (received {intensity})."
        )

    t_batch_start = time.perf_counter()

    # Flatten uploaded files (expanding ZIP if present)
    items_to_process: List[tuple[str, bytes]] = []

    for uf in files:
        filename = uf.filename or "unknown"
        suffix = Path(filename).suffix.lower()

        try:
            content = await uf.read()
        except Exception as e:
            logger.error("Failed to read uploaded file %s: %s", filename, e)
            continue

        if suffix == ".zip":
            try:
                zip_items = engine.unpack_zip_archive(content)
                items_to_process.extend(zip_items)
            except Exception as e:
                logger.warning("Error unpacking ZIP file %s: %s", filename, e)
                # Record error item
                items_to_process.append((filename, b"CORRUPTED_ZIP:" + str(e).encode()))
        elif suffix in SUPPORTED_IMAGE_EXTENSIONS:
            items_to_process.append((filename, content))
        else:
            # Unsupported extension
            items_to_process.append((filename, b"UNSUPPORTED_FORMAT"))

    if not items_to_process:
        raise HTTPException(status_code=400, detail="No valid images found in upload.")

    if len(items_to_process) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size ({len(items_to_process)}) exceeds maximum limit of {MAX_BATCH_FILES} files."
        )

    results: List[ImageInferenceResult] = []
    class_dist: Dict[str, int] = {}
    total_inf_time = 0.0
    successful_count = 0
    failed_count = 0

    for fname, data_bytes in items_to_process:
        if data_bytes == b"UNSUPPORTED_FORMAT":
            failed_count += 1
            results.append(ImageInferenceResult(
                filename=fname,
                status="error",
                error_message=f"Unsupported format '{Path(fname).suffix}'. Supported: {sorted(list(SUPPORTED_IMAGE_EXTENSIONS))}",
                file_size_bytes=0,
                condition_applied=condition,
                intensity_applied=intensity,
            ))
            continue

        if data_bytes.startswith(b"CORRUPTED_ZIP:"):
            failed_count += 1
            results.append(ImageInferenceResult(
                filename=fname,
                status="error",
                error_message=data_bytes.decode(errors="replace").split(":", 1)[1],
                file_size_bytes=0,
                condition_applied=condition,
                intensity_applied=intensity,
            ))
            continue

        raw_res = engine.process_image(
            image_bytes=data_bytes,
            filename=fname,
            model_mode=model_id,
            condition=condition,
            intensity=intensity,
        )

        res_obj = ImageInferenceResult(**raw_res)
        results.append(res_obj)

        if res_obj.status == "success":
            successful_count += 1
            # Add to class distribution (from robust model or first model in predictions)
            top_model = "robust_stain_aug" if "robust_stain_aug" in res_obj.predictions else next(iter(res_obj.predictions), None)
            if top_model:
                pred_c = res_obj.predictions[top_model].predicted_class
                class_dist[pred_c] = class_dist.get(pred_c, 0) + 1
                total_inf_time += res_obj.predictions[top_model].inference_time_ms
        else:
            failed_count += 1

    t_batch_end = time.perf_counter()
    total_batch_ms = round((t_batch_end - t_batch_start) * 1000.0, 2)
    avg_inf_ms = round(total_inf_time / max(successful_count, 1), 2)

    summary = BatchSummary(
        total_files=len(results),
        successful_files=successful_count,
        failed_files=failed_count,
        model_mode=model_id,
        condition=condition,
        intensity=intensity,
        total_inference_time_ms=total_batch_ms,
        average_inference_time_ms=avg_inf_ms,
        class_distribution=class_dist,
    )

    return PredictResponse(
        status="success" if successful_count > 0 else "error",
        summary=summary,
        results=results,
    )


@app.post("/predict/batch", response_model=PredictResponse)
async def predict_batch(
    files: List[UploadFile] = File(...),
    model_id: str = Form("robust_stain_aug"),
    condition: str = Form("original"),
    intensity: float = Form(1.0),
) -> PredictResponse:
    """Dedicated alias for batch prediction requests."""
    return await predict(files=files, model_id=model_id, condition=condition, intensity=intensity)
