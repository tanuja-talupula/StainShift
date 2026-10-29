"""
StainShift: Model Architectures for Histopathology Patch Classification
Optimized for efficient training and inference on both CPU and GPU.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
from torchvision import models

logger = logging.getLogger(__name__)

CLASS_NAMES: List[str] = [
    "ADI",   # Adipose
    "BACK",  # Background
    "DEB",   # Debris
    "LYM",   # Lymphocytes
    "MUC",   # Mucus
    "MUS",   # Smooth muscle
    "NORM",  # Normal colon mucosa
    "STR",   # Cancer-associated stroma
    "TUM"    # Colorectal adenocarcinoma epithelium
]

CLASS_DESCRIPTIONS: Dict[str, str] = {
    "ADI": "Adipose tissue (Fat)",
    "BACK": "Background (Glass / clear slide)",
    "DEB": "Debris (Necrotic tissue & artifacts)",
    "LYM": "Lymphocytes (Immune infiltration)",
    "MUC": "Mucus (Extracellular mucin pools)",
    "MUS": "Smooth muscle (Muscularis propria / mucosae)",
    "NORM": "Normal colon mucosa (Healthy crypts)",
    "STR": "Cancer-associated stroma (Desmoplastic)",
    "TUM": "Colorectal adenocarcinoma epithelium (Tumor)"
}

NUM_CLASSES: int = len(CLASS_NAMES)
SUPPORTED_ARCHITECTURES: List[str] = ["mobilenet_v3_small", "resnet18"]


def get_model(arch: str = "mobilenet_v3_small", pretrained: bool = True, num_classes: int = NUM_CLASSES) -> nn.Module:
    """
    Constructs a transfer-learning backbone adapted for histopathology patch classification.
    Options: 'mobilenet_v3_small' (fastest, ideal for CPU), 'resnet18'.
    """
    if arch == "mobilenet_v3_small":
        weights = models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
        model = models.mobilenet_v3_small(weights=weights)
        in_features = model.classifier[0].in_features
        model.classifier = nn.Sequential(
            nn.Linear(in_features, 256),
            nn.Hardswish(),
            nn.Dropout(p=0.2),
            nn.Linear(256, num_classes)
        )
    elif arch == "resnet18":
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        model = models.resnet18(weights=weights)
        in_features = model.fc.in_features
        model.fc = nn.Sequential(
            nn.Dropout(p=0.2),
            nn.Linear(in_features, num_classes)
        )
    else:
        raise ValueError(f"Unsupported architecture: '{arch}'. Supported: {SUPPORTED_ARCHITECTURES}")

    return model


def save_checkpoint(
    model: nn.Module,
    save_path: Union[str, Path],
    architecture: str,
    class_names: List[str],
    class_to_idx: Dict[str, int],
    epoch: int,
    metrics: Dict[str, float],
    train_mode: str,
    seed: int,
    preprocessing: Optional[Dict[str, Any]] = None,
    split_info: Optional[Dict[str, Any]] = None,
    commit_sha: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Saves a model checkpoint with complete scientific provenance metadata.
    Does not invent metadata. All fields must reflect the executed run.
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    checkpoint: Dict[str, Any] = {
        "format_version": 2,
        "provenance": "verified_run",
        "architecture": architecture,
        "class_names": list(class_names),
        "class_to_idx": dict(class_to_idx),
        "num_classes": len(class_names),
        "epoch": int(epoch),
        "metrics": dict(metrics),
        "train_mode": str(train_mode),
        "seed": int(seed),
        "preprocessing": preprocessing or {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
            "resize": None,
        },
        "split_info": split_info or {},
        "commit_sha": commit_sha,
        "model_state_dict": model.state_dict(),
    }
    if extra:
        checkpoint["extra"] = extra

    torch.save(checkpoint, save_path)
    logger.info("Saved verified checkpoint to %s (epoch %d)", save_path, epoch)


def load_checkpoint(
    checkpoint_path: Union[str, Path],
    expected_arch: Optional[str] = None,
    expected_classes: Optional[List[str]] = None,
    device: Union[str, torch.device] = "cpu",
    strict: bool = True,
    allow_legacy: bool = False,
) -> Tuple[nn.Module, Dict[str, Any]]:
    """
    Safely loads a trained checkpoint, validating existence, architecture,
    class mapping, and state-dict compatibility.

    Never falls back to random weights on missing files.
    Never guesses missing architecture or class mappings without explicit input.
    """
    path = Path(checkpoint_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Checkpoint file does not exist: {path}. "
            "Inference cannot proceed without a valid model checkpoint."
        )

    # Safe loading: weights_only=True when possible
    try:
        raw = torch.load(path, map_location=device, weights_only=True)
    except Exception:
        # Fallback for complex pickling in legacy checkpoints if trusted
        if not allow_legacy:
            raise
        raw = torch.load(path, map_location=device, weights_only=False)

    metadata: Dict[str, Any] = {}

    if isinstance(raw, dict) and "format_version" in raw and raw["format_version"] >= 2:
        # Modern verified format
        arch = raw.get("architecture")
        if expected_arch and arch != expected_arch:
            raise ValueError(
                f"Checkpoint architecture mismatch: checkpoint has '{arch}', "
                f"caller expected '{expected_arch}'."
            )
        classes = raw.get("class_names", CLASS_NAMES)
        if expected_classes and list(classes) != list(expected_classes):
            raise ValueError(
                f"Checkpoint class names mismatch: checkpoint has {classes}, "
                f"caller expected {expected_classes}."
            )
        state_dict = raw["model_state_dict"]
        metadata = {k: v for k, v in raw.items() if k != "model_state_dict"}
    elif isinstance(raw, dict) and "model_state_dict" in raw:
        # Legacy format (e.g. initial StainShift repository commit)
        if not allow_legacy:
            raise ValueError(
                f"Checkpoint at {path} is in legacy format without provenance metadata. "
                "Pass allow_legacy=True and specify expected_arch to load."
            )
        if not expected_arch:
            raise ValueError(
                "Cannot load legacy checkpoint without an explicitly specified expected_arch."
            )
        arch = expected_arch
        classes = expected_classes or CLASS_NAMES
        state_dict = raw["model_state_dict"]
        metadata = {
            "format_version": 1,
            "provenance": "legacy_unverified",
            "architecture": arch,
            "class_names": classes,
            "val_acc": raw.get("val_acc"),
            "val_f1": raw.get("val_f1"),
            "epoch": raw.get("epoch"),
            "report": raw.get("report"),
            "warning": "Historical checkpoint without complete training provenance metadata.",
        }
    elif isinstance(raw, dict) and all(isinstance(k, str) for k in raw.keys()):
        # Raw state dict
        if not allow_legacy:
            raise ValueError(
                f"Checkpoint at {path} contains only raw state dict weights. "
                "Pass allow_legacy=True and specify expected_arch to load."
            )
        if not expected_arch:
            raise ValueError(
                "Cannot load raw state-dict checkpoint without expected_arch."
            )
        arch = expected_arch
        classes = expected_classes or CLASS_NAMES
        state_dict = raw
        metadata = {
            "format_version": 0,
            "provenance": "legacy_raw_state_dict",
            "architecture": arch,
            "class_names": classes,
            "warning": "Raw state dict loaded without provenance metadata.",
        }
    else:
        raise ValueError(f"Unrecognized checkpoint object structure in {path}: {type(raw)}")

    model = get_model(arch=arch, pretrained=False, num_classes=len(classes))
    try:
        model.load_state_dict(state_dict, strict=strict)
    except RuntimeError as err:
        raise ValueError(
            f"Failed to load state dict from {path} into architecture '{arch}': {err}"
        ) from err

    model.to(device)
    model.eval()
    return model, metadata
