"""
Pydantic schemas for StainShift AI Inference API.
Defines strict, validated data contracts for single and batch predictions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    id: str = Field(..., description="Unique model identifier: 'baseline' or 'robust_stain_aug'")
    name: str = Field(..., description="Human-readable model name")
    architecture: str = Field(..., description="Neural network architecture")
    checkpoint_sha256: str = Field(..., description="SHA-256 hash of loaded checkpoint")
    num_classes: int = Field(default=9, description="Number of output tissue classes")
    classes: List[str] = Field(..., description="List of 9 class abbreviations")
    description: str = Field(..., description="Scientific description of training regimen")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall backend health status ('healthy' or 'degraded')")
    version: str = Field(default="1.0.0", description="API version")
    device: str = Field(..., description="Active compute device ('cpu', 'mps', or 'cuda')")
    models_available: Dict[str, bool] = Field(..., description="Availability status for each model")
    models: List[ModelInfo] = Field(default_factory=list, description="Metadata for loaded models")
    supported_formats: List[str] = Field(..., description="Supported file extensions")
    supported_conditions: List[str] = Field(..., description="Supported stain shift conditions")


class SingleModelPrediction(BaseModel):
    model_id: str
    model_name: str
    predicted_class: str
    predicted_class_description: str
    confidence: float
    probabilities: Dict[str, float]
    inference_time_ms: float


class ImageInferenceResult(BaseModel):
    filename: str
    status: str  # "success" or "error"
    error_message: Optional[str] = None
    original_dimensions: Optional[List[int]] = None  # [width, height]
    file_size_bytes: int
    condition_applied: str
    intensity_applied: float
    original_thumbnail_b64: Optional[str] = None  # data:image/png;base64,...
    transformed_thumbnail_b64: Optional[str] = None
    predictions: Dict[str, SingleModelPrediction] = Field(
        default_factory=dict,
        description="Keyed by model_id (e.g. 'baseline', 'robust_stain_aug')"
    )
    agreement: Optional[bool] = Field(
        default=None,
        description="True if baseline and robust models agree on predicted class in comparison mode"
    )


class BatchSummary(BaseModel):
    total_files: int
    successful_files: int
    failed_files: int
    model_mode: str  # "baseline", "robust_stain_aug", or "compare"
    condition: str
    intensity: float
    total_inference_time_ms: float
    average_inference_time_ms: float
    class_distribution: Dict[str, int]


class PredictResponse(BaseModel):
    status: str
    summary: BatchSummary
    results: List[ImageInferenceResult]
