"""
StainShift Real Model Inference Engine.
Loads existing trained PyTorch checkpoints, validates input images,
executes physics-based stain transformations, and computes exact model predictions.
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import zipfile

import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
import torchvision.transforms as T

from src.dataset import IMAGENET_MEAN, IMAGENET_STD
from src.models import (
    CLASS_NAMES,
    CLASS_DESCRIPTIONS,
    NUM_CLASSES,
    load_checkpoint,
)
from src.stain_shift import (
    DISTINCT_STAIN_PROFILES,
    STAIN_PROFILES,
    MacenkoStainDecomposer,
    apply_stain_profile,
)

logger = logging.getLogger(__name__)

# Security & Processing Constraints
MAX_SINGLE_FILE_BYTES: int = 15 * 1024 * 1024      # 15 MB per image
MAX_ZIP_TOTAL_BYTES: int = 100 * 1024 * 1024       # 100 MB max uncompressed ZIP
MAX_BATCH_FILES: int = 50                          # Max 50 files per request
MAX_IMAGE_DIMENSION: int = 4096                    # Max 4096 px width/height
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
SUPPORTED_ARCHIVE_EXTENSIONS = {".zip"}


def compute_sha256(filepath: Union[str, Path]) -> str:
    """Computes SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def image_to_base64_thumbnail(img: Image.Image, size: Tuple[int, int] = (224, 224)) -> str:
    """Creates a compact base64-encoded PNG thumbnail data URL."""
    thumb = img.copy()
    thumb.thumbnail(size, Image.Resampling.BILINEAR)
    buffer = io.BytesIO()
    thumb.save(buffer, format="PNG", optimize=True)
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


class InferenceEngine:
    """
    Production inference engine maintaining loaded PyTorch models,
    preprocessing pipelines, and stain transformation modules.
    """

    def __init__(
        self,
        models_dir: Union[str, Path] = "models/full_benchmark_20261029_1838",
        device: Optional[str] = None,
    ):
        self.models_dir = Path(models_dir)
        self.device_str = device or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.device = torch.device(self.device_str)

        self.models: Dict[str, torch.nn.Module] = {}
        self.model_metadata: Dict[str, Dict[str, Any]] = {}
        self.decomposer = MacenkoStainDecomposer()

        # Tensor transform for model input
        self.tensor_transform = T.Compose([
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
        ])

        self._load_checkpoints()

    def _load_checkpoints(self) -> None:
        """Loads baseline and robust models from existing checkpoints."""
        checkpoints = {
            "baseline": {
                "filename": "baseline.pth",
                "name": "Baseline Model",
                "desc": "Standard empirical risk minimization with geometric augmentations only."
            },
            "robust_stain_aug": {
                "filename": "robust_stain_aug.pth",
                "name": "Stain-Robust Model",
                "desc": "Physics-informed training with online Macenko Beer-Lambert stain augmentation."
            }
        }

        for model_id, info in checkpoints.items():
            ckpt_path = self.models_dir / info["filename"]
            if not ckpt_path.is_file():
                logger.warning("Checkpoint not found at %s. Model %s unavailable.", ckpt_path, model_id)
                continue

            try:
                sha256 = compute_sha256(ckpt_path)
                model, meta = load_checkpoint(
                    ckpt_path,
                    expected_arch="mobilenet_v3_small",
                    expected_classes=CLASS_NAMES,
                    device=self.device_str,
                    strict=True,
                )
                model.eval()
                self.models[model_id] = model
                self.model_metadata[model_id] = {
                    "id": model_id,
                    "name": info["name"],
                    "architecture": meta.get("architecture", "mobilenet_v3_small"),
                    "checkpoint_sha256": sha256,
                    "num_classes": NUM_CLASSES,
                    "classes": CLASS_NAMES,
                    "description": info["desc"],
                    "epoch": meta.get("epoch", None),
                    "metrics": meta.get("metrics", {}),
                }
                logger.info("Successfully loaded %s from %s (SHA-256: %s)", model_id, ckpt_path, sha256[:12])
            except Exception as e:
                logger.error("Failed to load checkpoint %s: %s", ckpt_path, e)

    def is_model_available(self, model_id: str) -> bool:
        return model_id in self.models

    def get_available_models(self) -> List[Dict[str, Any]]:
        return list(self.model_metadata.values())

    def apply_transformation(
        self,
        img_rgb: Image.Image,
        condition: str,
        intensity: float = 1.0,
    ) -> Tuple[Image.Image, Optional[str]]:
        """
        Applies requested stain condition and intensity scaling.
        Returns: (transformed_pil_image, error_note_if_any)
        """
        if condition == "original":
            return img_rgb.copy(), None

        img_np = np.array(img_rgb)

        if condition == "reconstruction_only":
            try:
                rec_np = self.decomposer.reconstruct(img_np)
                return Image.fromarray(rec_np), None
            except Exception as err:
                logger.warning("Reconstruction failed, falling back: %s", err)
                return img_rgb.copy(), f"Reconstruction failed: {err}"

        if condition not in STAIN_PROFILES:
            raise ValueError(f"Unknown condition '{condition}'. Supported: {DISTINCT_STAIN_PROFILES}")

        cfg = STAIN_PROFILES[condition]
        base_h = cfg["alpha_h"]
        base_e = cfg["alpha_e"]
        base_rot = cfg["stain_rot_deg"]

        # Scale perturbation intensity:
        # intensity == 1.0 -> exact benchmark condition
        # intensity == 0.0 -> neutral (alpha_h=1, alpha_e=1, rot=0)
        eff_h = 1.0 + float(intensity) * (base_h - 1.0)
        eff_e = 1.0 + float(intensity) * (base_e - 1.0)
        eff_rot = float(intensity) * base_rot

        try:
            perturbed_np = self.decomposer.perturb(
                img_np,
                alpha_h=eff_h,
                alpha_e=eff_e,
                stain_rot_deg=eff_rot,
            )
            return Image.fromarray(perturbed_np), None
        except Exception as err:
            logger.warning("Stain shift failed (%s, intensity=%.2f): %s", condition, intensity, err)
            return img_rgb.copy(), f"Stain shift failed: {err}"

    def run_single_model_inference(
        self,
        model_id: str,
        tensor_224: torch.Tensor,
    ) -> Dict[str, Any]:
        """Runs forward inference on a preprocessed (1, 3, 224, 224) tensor."""
        if model_id not in self.models:
            raise KeyError(f"Model '{model_id}' is not loaded or available.")

        model = self.models[model_id]
        meta = self.model_metadata[model_id]

        tensor_device = tensor_224.to(self.device)

        if self.device_str == "mps":
            torch.mps.synchronize()
        elif self.device_str == "cuda":
            torch.cuda.synchronize()

        t0 = time.perf_counter()
        with torch.no_grad():
            logits = model(tensor_device)
            probs = F.softmax(logits, dim=1)[0]
        if self.device_str == "mps":
            torch.mps.synchronize()
        elif self.device_str == "cuda":
            torch.cuda.synchronize()
        t1 = time.perf_counter()

        elapsed_ms = round((t1 - t0) * 1000.0, 3)

        probs_np = probs.cpu().numpy()
        pred_idx = int(np.argmax(probs_np))
        pred_class = CLASS_NAMES[pred_idx]
        confidence = float(probs_np[pred_idx])

        prob_dict = {
            cname: round(float(probs_np[i]), 4)
            for i, cname in enumerate(CLASS_NAMES)
        }

        return {
            "model_id": model_id,
            "model_name": meta["name"],
            "predicted_class": pred_class,
            "predicted_class_description": CLASS_DESCRIPTIONS.get(pred_class, pred_class),
            "confidence": round(confidence, 4),
            "probabilities": prob_dict,
            "inference_time_ms": elapsed_ms,
        }

    def process_image(
        self,
        image_bytes: bytes,
        filename: str,
        model_mode: str = "robust_stain_aug",  # "baseline", "robust_stain_aug", or "compare"
        condition: str = "original",
        intensity: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Validates, transforms, and runs inference on a single image byte stream.
        """
        file_size = len(image_bytes)
        if file_size > MAX_SINGLE_FILE_BYTES:
            return {
                "filename": filename,
                "status": "error",
                "error_message": f"File size ({file_size / (1024*1024):.1f} MB) exceeds limit of {MAX_SINGLE_FILE_BYTES / (1024*1024):.0f} MB.",
                "file_size_bytes": file_size,
                "condition_applied": condition,
                "intensity_applied": intensity,
                "predictions": {},
            }

        # Validate image format via PIL
        try:
            with Image.open(io.BytesIO(image_bytes)) as pil_img:
                pil_format = pil_img.format
                if pil_img.mode not in ("RGB", "RGBA"):
                    return {
                        "filename": filename,
                        "status": "error",
                        "error_message": f"Unsupported image mode '{pil_img.mode}'. Only 8-bit RGB/RGBA pathology images are supported.",
                        "file_size_bytes": file_size,
                        "condition_applied": condition,
                        "intensity_applied": intensity,
                        "predictions": {},
                    }
                width, height = pil_img.size
                if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                    return {
                        "filename": filename,
                        "status": "error",
                        "error_message": f"Image dimensions ({width}x{height}) exceed maximum limit of {MAX_IMAGE_DIMENSION}px.",
                        "file_size_bytes": file_size,
                        "condition_applied": condition,
                        "intensity_applied": intensity,
                        "predictions": {},
                    }
                # Normalize to standard 8-bit RGB
                rgb_img = pil_img.convert("RGB")
        except Exception as e:
            return {
                "filename": filename,
                "status": "error",
                "error_message": f"Failed to parse image file: {e}",
                "file_size_bytes": file_size,
                "condition_applied": condition,
                "intensity_applied": intensity,
                "predictions": {},
            }

        # Generate base64 thumbnail of original
        orig_thumb = image_to_base64_thumbnail(rgb_img, (224, 224))

        # Apply stain transformation if requested
        transformed_img, transform_error = self.apply_transformation(rgb_img, condition, intensity)
        trans_thumb = image_to_base64_thumbnail(transformed_img, (224, 224))

        # Prepare 224x224 tensor for model input
        input_224 = transformed_img.resize((224, 224), Image.Resampling.BILINEAR)
        tensor = self.tensor_transform(input_224).unsqueeze(0)

        # Run inference based on model_mode
        models_to_run = (
            ["baseline", "robust_stain_aug"]
            if model_mode in ("compare", "both")
            else [model_mode]
        )

        predictions: Dict[str, Any] = {}
        agreement: Optional[bool] = None

        for mid in models_to_run:
            if not self.is_model_available(mid):
                return {
                    "filename": filename,
                    "status": "error",
                    "error_message": f"Requested model '{mid}' is not available.",
                    "original_dimensions": [width, height],
                    "file_size_bytes": file_size,
                    "condition_applied": condition,
                    "intensity_applied": intensity,
                    "original_thumbnail_b64": orig_thumb,
                    "transformed_thumbnail_b64": trans_thumb,
                    "predictions": {},
                }
            pred = self.run_single_model_inference(mid, tensor)
            predictions[mid] = pred

        if len(predictions) == 2:
            base_pred = predictions.get("baseline", {}).get("predicted_class")
            rob_pred = predictions.get("robust_stain_aug", {}).get("predicted_class")
            agreement = (base_pred == rob_pred)

        return {
            "filename": filename,
            "status": "success",
            "error_message": transform_error,
            "original_dimensions": [width, height],
            "file_size_bytes": file_size,
            "condition_applied": condition,
            "intensity_applied": intensity,
            "original_thumbnail_b64": orig_thumb,
            "transformed_thumbnail_b64": trans_thumb,
            "predictions": predictions,
            "agreement": agreement,
        }

    def unpack_zip_archive(self, zip_bytes: bytes) -> List[Tuple[str, bytes]]:
        """
        Safely unpacks a ZIP archive with security protections:
        - Prevents zip slip / path traversal.
        - Prevents zip bombs (max total uncompressed bytes).
        - Skips hidden OS files and folders.
        """
        extracted_files: List[Tuple[str, bytes]] = []
        total_uncompressed = 0

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            infolist = zf.infolist()
            if len(infolist) > MAX_BATCH_FILES * 2:
                raise ValueError(f"ZIP contains {len(infolist)} entries; maximum allowed is {MAX_BATCH_FILES}.")

            for info in infolist:
                # Disallow directories
                if info.is_dir():
                    continue

                # Disallow absolute paths and path traversal ('../')
                clean_name = Path(info.filename).name
                if not clean_name or clean_name.startswith((".", "__MACOSX")):
                    continue

                # Check extension
                suffix = Path(clean_name).suffix.lower()
                if suffix not in SUPPORTED_IMAGE_EXTENSIONS:
                    continue

                # Check zip bomb protection
                total_uncompressed += info.file_size
                if total_uncompressed > MAX_ZIP_TOTAL_BYTES:
                    raise ValueError(
                        f"Uncompressed ZIP size exceeds safety limit of {MAX_ZIP_TOTAL_BYTES / (1024*1024):.0f} MB."
                    )

                if len(extracted_files) >= MAX_BATCH_FILES:
                    break

                with zf.open(info) as f:
                    file_bytes = f.read()
                    extracted_files.append((clean_name, file_bytes))

        return extracted_files
