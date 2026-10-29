"""
StainShift: Histopathology Dataset Loader and Augmentations
Handles dataset partitioning, standard transforms, stain augmentation,
and synthetic stain shift evaluations for colorectal cancer histopathology patches.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image
import torch
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as T

from .models import CLASS_NAMES
from .stain_shift import (
    STAIN_PROFILES,
    DegenerateTissueError,
    InsufficientTissueError,
    MacenkoStainDecomposer,
    StainDecompositionError,
    apply_stain_profile,
)

logger = logging.getLogger(__name__)

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Standard supported transform modes
SUPPORTED_TRANSFORM_MODES = [
    "train_standard",          # Geometric augmentation only (flips, 90-degree rotations)
    "train_stain_augmented",   # Geometric + physics-based Macenko stain perturbation
    "stain_augmented",         # Backward-compatibility alias for train_stain_augmented
    "eval_standard",           # Evaluation on unmodified original images
    "eval",                    # Alias for eval_standard
    "standard",                # Alias for eval_standard
    "eval_reconstruction",     # Evaluation on deconvolution/reconstruction control
    "eval_shifted",            # Evaluation under a designated stain profile
]
VALID_IMAGE_EXTENSIONS = {".png", ".tif", ".tiff"}


def scan_dataset_files(data_dir: Union[str, Path]) -> Dict[str, List[Path]]:
    """
    Scans a dataset directory for colorectal cancer histology patches.
    Supports:
    1. Nested class folders: data_dir/<CLASS>/*.(png|tif|tiff)
    2. Flat named files: data_dir/<CLASS>-*.(png|tif|tiff)
    3. Wrapped nested folders: data_dir/<ARCHIVE_NAME>/<CLASS>/*.(png|tif|tiff)

    Returns a dict mapping canonical class names to sorted lists of Path objects.
    Files are sorted deterministically using their POSIX relative path.
    """
    data_path = Path(data_dir).resolve()
    if not data_path.is_dir():
        raise FileNotFoundError(f"Dataset directory does not exist: {data_path}")

    class_to_idx = {name: i for i, name in enumerate(CLASS_NAMES)}
    class_files: Dict[str, List[Path]] = {name: [] for name in CLASS_NAMES}

    # Discover candidate files recursively to support flat, nested, and wrapped archive layouts
    candidates = [
        p for p in data_path.rglob("*")
        if p.is_file() and p.suffix.lower() in VALID_IMAGE_EXTENSIONS and not p.name.startswith(".")
    ]

    if not candidates:
        raise FileNotFoundError(
            f"No valid histology image files ({', '.join(sorted(VALID_IMAGE_EXTENSIONS))}) found in '{data_path}'"
        )

    for fpath in candidates:
        cname = None
        # Priority 1: Direct parent folder name
        if fpath.parent.name in class_to_idx:
            cname = fpath.parent.name
        else:
            # Priority 2: Stem prefix separated by '-' or '_'
            stem_prefix = fpath.stem.split("-")[0].split("_")[0]
            if stem_prefix in class_to_idx:
                cname = stem_prefix

        if cname is not None:
            class_files[cname].append(fpath)

    # Deterministically sort files within each class by relative POSIX path
    for cname in class_files:
        class_files[cname].sort(key=lambda p: p.relative_to(data_path).as_posix())

    # Validate that at least one valid class was found
    total_found = sum(len(fls) for fls in class_files.values())
    if total_found == 0:
        raise ValueError(
            f"Found image files in '{data_path}', but none matched expected class names: {CLASS_NAMES}. "
            "Ensure files are organized in class subfolders (e.g. data/TUM/patch.tif) or prefixed with class name (e.g. data/TUM-001.png)."
        )

    return class_files


class CRCDataset(Dataset):
    """
    PyTorch Dataset for CRC Histopathology Patches.
    Supports standard training, stain-augmented training, and controlled stain-shift evaluations.
    """

    def __init__(
        self,
        file_paths: List[Union[str, Path]],
        labels: List[int],
        transform_mode: str = "eval_standard",
        stain_profile: str = "original",
        seed: Optional[int] = None,
        fail_mode: str = "fallback_and_record",  # 'fallback_and_record' or 'raise'
    ):
        if transform_mode not in SUPPORTED_TRANSFORM_MODES:
            raise ValueError(
                f"Unsupported transform_mode: '{transform_mode}'. "
                f"Supported modes: {SUPPORTED_TRANSFORM_MODES}"
            )
        if stain_profile not in STAIN_PROFILES:
            raise ValueError(
                f"Unknown stain profile: '{stain_profile}'. "
                f"Available profiles: {list(STAIN_PROFILES.keys())}"
            )

        self.file_paths = [str(p) for p in file_paths]
        self.labels = list(labels)
        self.transform_mode = transform_mode
        self.stain_profile = stain_profile
        self.fail_mode = fail_mode
        self.rng = random.Random(seed) if seed is not None else random.Random()

        # Initialize the Macenko decomposer whenever stain augmentation, reconstruction,
        # or non-neutral shift evaluation is requested.
        needs_decomposer = (
            self.transform_mode in ("train_stain_augmented", "stain_augmented", "eval_reconstruction")
            or (self.transform_mode == "eval_shifted" and self.stain_profile not in ("original", None))
        )
        self.decomposer = MacenkoStainDecomposer() if needs_decomposer else None

        # Tracking transformation outcomes
        self.transform_stats: Dict[str, Any] = {
            "attempts": 0,
            "successes": 0,
            "neutral_skips": 0,
            "probabilistic_skips": 0,
            "failures": 0,
            "failure_records": [],
        }

        # Baseline normalization transform
        self.base_tensor_transform = T.Compose([
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
        ])

    def __len__(self) -> int:
        return len(self.file_paths)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, str]:
        img_path = self.file_paths[idx]
        label = self.labels[idx]

        # Load standard 8-bit RGB/RGBA pathology image
        try:
            with Image.open(img_path) as img:
                if img.mode not in ("RGB", "RGBA"):
                    raise ValueError(
                        f"Unsupported image mode '{img.mode}' in '{img_path}'. "
                        "StainShift requires standard 8-bit RGB (or RGBA) pathology patches. "
                        "Unsupported depths (e.g. 16-bit, palette, grayscale) are rejected."
                    )
                img = img.convert("RGB")
        except Exception as err:
            raise RuntimeError(f"Failed to read image at '{img_path}': {err}") from err

        # 1. Standard training mode: Geometric only (flips and discrete 90-degree rotations)
        if self.transform_mode == "train_standard":
            if self.rng.random() > 0.5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if self.rng.random() > 0.5:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            rot = self.rng.choice([0, 90, 180, 270])
            if rot > 0:
                img = img.rotate(rot)
            tensor = self.base_tensor_transform(img)

        # 2. Stain-augmented training mode: Geometric + Macenko perturbation
        elif self.transform_mode in ("train_stain_augmented", "stain_augmented"):
            # Geometric
            if self.rng.random() > 0.5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if self.rng.random() > 0.5:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            rot = self.rng.choice([0, 90, 180, 270])
            if rot > 0:
                img = img.rotate(rot)

            # Stain Augmentation: OD perturbation with 60% probability
            img_np = np.array(img)
            self.transform_stats["attempts"] += 1

            if self.rng.random() < 0.60:
                alpha_h = self.rng.uniform(0.70, 1.40)
                alpha_e = self.rng.uniform(0.70, 1.40)
                rot_deg = self.rng.uniform(-4.0, 4.0)

                # Ensure decomposer is present (guaranteed by __init__)
                if self.decomposer is None:
                    raise RuntimeError(
                        f"Decomposer was not initialized for transform mode '{self.transform_mode}'. "
                        "This is a programming defect that must not be swallowed."
                    )

                try:
                    img_np = self.decomposer.perturb(
                        img_np, alpha_h=alpha_h, alpha_e=alpha_e, stain_rot_deg=rot_deg
                    )
                    self.transform_stats["successes"] += 1
                except (StainDecompositionError, InsufficientTissueError, DegenerateTissueError, ValueError) as err:
                    self.transform_stats["failures"] += 1
                    self.transform_stats["failure_records"].append({
                        "file_path": img_path,
                        "mode": self.transform_mode,
                        "reason": str(err),
                    })
                    if self.fail_mode == "raise":
                        raise
                    # In fallback_and_record, image remains the geometrically transformed RGB patch
                    logger.debug("Stain augmentation fallback on %s: %s", img_path, err)
            else:
                self.transform_stats["probabilistic_skips"] += 1

            tensor = self.base_tensor_transform(Image.fromarray(img_np))

        # 3. Reconstruction-only evaluation control (isolating deconvolution loss)
        elif self.transform_mode == "eval_reconstruction":
            img_np = np.array(img)
            self.transform_stats["attempts"] += 1
            if self.decomposer is None:
                raise RuntimeError("Decomposer not initialized for eval_reconstruction.")
            try:
                img_np = self.decomposer.reconstruct(img_np)
                self.transform_stats["successes"] += 1
            except (StainDecompositionError, InsufficientTissueError, DegenerateTissueError, ValueError) as err:
                self.transform_stats["failures"] += 1
                self.transform_stats["failure_records"].append({
                    "file_path": img_path,
                    "mode": self.transform_mode,
                    "reason": str(err),
                })
                if self.fail_mode == "raise":
                    raise
            tensor = self.base_tensor_transform(Image.fromarray(img_np))

        # 4. Shifted evaluation under designated stain profile
        elif self.transform_mode == "eval_shifted":
            img_np = np.array(img)
            self.transform_stats["attempts"] += 1
            if self.stain_profile == "original":
                self.transform_stats["neutral_skips"] += 1
                tensor = self.base_tensor_transform(img)
            else:
                try:
                    img_np = apply_stain_profile(img_np, self.stain_profile)
                    self.transform_stats["successes"] += 1
                except (StainDecompositionError, InsufficientTissueError, DegenerateTissueError, ValueError) as err:
                    self.transform_stats["failures"] += 1
                    self.transform_stats["failure_records"].append({
                        "file_path": img_path,
                        "mode": self.transform_mode,
                        "stain_profile": self.stain_profile,
                        "reason": str(err),
                    })
                    if self.fail_mode == "raise":
                        raise
                tensor = self.base_tensor_transform(Image.fromarray(img_np))

        # 5. Standard in-domain unmodified evaluation
        else:
            tensor = self.base_tensor_transform(img)

        return tensor, label, img_path


def get_data_splits(
    data_dir: Union[str, Path],
    splits_cache: Optional[Union[str, Path]] = None,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    patient_grouping: bool = False,
    max_samples_per_class: Optional[int] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Creates or loads stratified train / val / test splits across all classes.

    Ensures:
    - Deterministic file sorting before random shuffling.
    - Verified disjointness between train, val, and test splits.
    - Rejection of empty splits.
    - Path persistence supporting relative paths for portability.
    """
    data_path = Path(data_dir)
    if not data_path.is_dir():
        raise FileNotFoundError(f"Dataset directory does not exist: {data_path}")

    # If cache exists and is valid, load it
    if splits_cache:
        cache_path = Path(splits_cache)
        if cache_path.is_file():
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            train_files = [str(data_path / f) if not Path(f).is_absolute() else f for f in cached["train"]["files"]]
            val_files = [str(data_path / f) if not Path(f).is_absolute() else f for f in cached["val"]["files"]]
            test_files = [str(data_path / f) if not Path(f).is_absolute() else f for f in cached["test"]["files"]]

            # Verify that cached files actually exist
            missing = [f for f in train_files + val_files + test_files if not Path(f).is_file()]
            if missing:
                logger.warning(
                    "Splits cache at %s contains %d missing files; regenerating split.",
                    cache_path, len(missing)
                )
            else:
                return (
                    {"files": train_files, "labels": cached["train"]["labels"]},
                    {"files": val_files, "labels": cached["val"]["labels"]},
                    {"files": test_files, "labels": cached["test"]["labels"]},
                )

    # Deterministic multi-layout file scanning
    class_files = scan_dataset_files(data_path)
    class_to_idx = {name: i for i, name in enumerate(CLASS_NAMES)}

    # Validate that classes are represented
    empty_classes = [c for c, fls in class_files.items() if len(fls) == 0]
    if empty_classes:
        logger.warning("Classes with zero files found in %s: %s", data_path, empty_classes)

    rng = random.Random(seed)
    train_data: Dict[str, List[Any]] = {"files": [], "labels": []}
    val_data: Dict[str, List[Any]] = {"files": [], "labels": []}
    test_data: Dict[str, List[Any]] = {"files": [], "labels": []}

    for cname in sorted(class_files.keys()):
        files = list(class_files[cname])
        # Sort before shuffling to guarantee platform-independent determinism
        files.sort()
        rng.shuffle(files)
        if max_samples_per_class is not None and len(files) > max_samples_per_class:
            files = files[:max_samples_per_class]

        n = len(files)
        if n >= 3:
            n_val = max(1, int(n * val_ratio))
            n_test = max(1, int(n * test_ratio))
            n_train = max(1, n - n_val - n_test)
            c_train = files[:n_train]
            c_val = files[n_train:n_train + n_val]
            c_test = files[n_train + n_val:]
        else:
            c_train = files[:1]
            c_val = files[1:2]
            c_test = files[2:]

        lbl = class_to_idx[cname]

        train_data["files"].extend([str(p) for p in c_train])
        train_data["labels"].extend([lbl] * len(c_train))

        val_data["files"].extend([str(p) for p in c_val])
        val_data["labels"].extend([lbl] * len(c_val))

        test_data["files"].extend([str(p) for p in c_test])
        test_data["labels"].extend([lbl] * len(c_test))

    # Reject empty splits
    if len(train_data["files"]) == 0 or len(val_data["files"]) == 0 or len(test_data["files"]) == 0:
        raise ValueError(
            f"Generated an empty split! Train: {len(train_data['files'])}, "
            f"Val: {len(val_data['files'])}, Test: {len(test_data['files'])}"
        )

    # Disjointness validation (no sample leakage across partitions)
    train_set = set(train_data["files"])
    val_set = set(val_data["files"])
    test_set = set(test_data["files"])

    if train_set & val_set:
        raise ValueError(f"Train and Val splits share {len(train_set & val_set)} samples!")
    if train_set & test_set:
        raise ValueError(f"Train and Test splits share {len(train_set & test_set)} samples!")
    if val_set & test_set:
        raise ValueError(f"Val and Test splits share {len(val_set & test_set)} samples!")

    # Save cache with portable relative paths
    if splits_cache:
        cache_path = Path(splits_cache)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        rel_splits = {
            "metadata": {
                "dataset_name": data_path.name,
                "seed": seed,
                "train_ratio": train_ratio,
                "val_ratio": val_ratio,
                "test_ratio": test_ratio,
                "num_samples": len(train_set) + len(val_set) + len(test_set),
            },
            "train": {
                "files": [str(Path(f).relative_to(data_path)) if Path(f).is_relative_to(data_path) else f for f in train_data["files"]],
                "labels": train_data["labels"]
            },
            "val": {
                "files": [str(Path(f).relative_to(data_path)) if Path(f).is_relative_to(data_path) else f for f in val_data["files"]],
                "labels": val_data["labels"]
            },
            "test": {
                "files": [str(Path(f).relative_to(data_path)) if Path(f).is_relative_to(data_path) else f for f in test_data["files"]],
                "labels": test_data["labels"]
            },
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(rel_splits, f, indent=2)

    return train_data, val_data, test_data


def build_dataloaders(
    data_dir: Union[str, Path],
    splits_cache: Optional[Union[str, Path]] = None,
    batch_size: int = 32,
    num_workers: int = 0,
    train_mode: str = "train_standard",
    seed: int = 42,
    max_samples_per_class: Optional[int] = None,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """Builds PyTorch DataLoaders for train, val, and test splits."""
    train_split, val_split, test_split = get_data_splits(
        data_dir, splits_cache=splits_cache, seed=seed, max_samples_per_class=max_samples_per_class
    )

    train_ds = CRCDataset(
        train_split["files"], train_split["labels"], transform_mode=train_mode, seed=seed
    )
    val_ds = CRCDataset(
        val_split["files"], val_split["labels"], transform_mode="eval_standard", seed=seed + 1
    )
    test_ds = CRCDataset(
        test_split["files"], test_split["labels"], transform_mode="eval_standard", seed=seed + 2
    )

    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )
    test_loader = DataLoader(
        test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )

    return train_loader, val_loader, test_loader
