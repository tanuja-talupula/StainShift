"""
StainShift: Histopathology Dataset Loader and Augmentations
Handles dataset partitioning, standard transforms, stain augmentation,
and synthetic stain shift evaluations for the CRC-VAL-HE-7K dataset.
"""

import os
import json
import random
import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T

from .stain_shift import MacenkoStainDecomposer, apply_stain_profile, STAIN_PROFILES
from .models import CLASS_NAMES


IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


class CRCDataset(Dataset):
    """
    PyTorch Dataset for CRC Histopathology Patches.
    Supports standard, stain-augmented, and stain-shifted evaluation pipelines.
    """

    def __init__(self, file_paths, labels, transform_mode="standard", stain_profile="original"):
        self.file_paths = file_paths
        self.labels = labels
        self.transform_mode = transform_mode
        self.stain_profile = stain_profile
        self.decomposer = MacenkoStainDecomposer() if transform_mode == "stain_augmented" or stain_profile != "original" else None

        # Standard baseline normalization
        self.base_tensor_transform = T.Compose([
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
        ])

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, idx):
        img_path = self.file_paths[idx]
        label = self.labels[idx]

        # Load RGB image
        with Image.open(img_path) as img:
            img = img.convert("RGB")

        # Apply transforms based on mode
        if self.transform_mode == "train_standard":
            # Baseline data augmentation (geometric only)
            if random.random() > 0.5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if random.random() > 0.5:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            rot = random.choice([0, 90, 180, 270])
            if rot > 0:
                img = img.rotate(rot)
            tensor = self.base_tensor_transform(img)

        elif self.transform_mode == "train_stain_augmented":
            # Geometric augmentation
            if random.random() > 0.5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if random.random() > 0.5:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            rot = random.choice([0, 90, 180, 270])
            if rot > 0:
                img = img.rotate(rot)

            # Stain Augmentation: random OD perturbation with 60% probability
            img_np = np.array(img)
            if random.random() < 0.60:
                alpha_h = random.uniform(0.70, 1.40)
                alpha_e = random.uniform(0.70, 1.40)
                rot_deg = random.uniform(-4.0, 4.0)
                try:
                    img_np = self.decomposer.perturb(img_np, alpha_h=alpha_h, alpha_e=alpha_e, stain_rot_deg=rot_deg)
                except Exception:
                    pass  # Fallback to original if singular matrix
            tensor = self.base_tensor_transform(Image.fromarray(img_np))

        elif self.transform_mode == "eval_shifted":
            # Evaluation under a specific stain shift profile
            img_np = np.array(img)
            if self.stain_profile != "original":
                try:
                    img_np = apply_stain_profile(img_np, self.stain_profile)
                except Exception:
                    pass
            tensor = self.base_tensor_transform(Image.fromarray(img_np))

        else:  # Standard eval (in-domain)
            tensor = self.base_tensor_transform(img)

        return tensor, label, img_path


def get_data_splits(data_dir: str, splits_cache: str = None, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42):
    """
    Creates or loads a stratified train / val / test split across all 9 classes.
    """
    if splits_cache and os.path.exists(splits_cache):
        with open(splits_cache, "r") as f:
            splits = json.load(f)
        return splits["train"], splits["val"], splits["test"]

    random.seed(seed)
    np.random.seed(seed)

    class_to_idx = {name: i for i, name in enumerate(CLASS_NAMES)}
    class_files = {name: [] for name in CLASS_NAMES}

    for fname in os.listdir(data_dir):
        if not fname.endswith(".png"):
            continue
        cname = fname.split("-")[0]
        if cname in class_to_idx:
            class_files[cname].append(os.path.join(data_dir, fname))

    train_data = {"files": [], "labels": []}
    val_data = {"files": [], "labels": []}
    test_data = {"files": [], "labels": []}

    for cname, files in sorted(class_files.items()):
        random.shuffle(files)
        n = len(files)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        c_train = files[:n_train]
        c_val = files[n_train:n_train + n_val]
        c_test = files[n_train + n_val:]

        lbl = class_to_idx[cname]

        train_data["files"].extend(c_train)
        train_data["labels"].extend([lbl] * len(c_train))

        val_data["files"].extend(c_val)
        val_data["labels"].extend([lbl] * len(c_val))

        test_data["files"].extend(c_test)
        test_data["labels"].extend([lbl] * len(c_test))

    splits = {"train": train_data, "val": val_data, "test": test_data}

    if splits_cache:
        os.makedirs(os.path.dirname(splits_cache), exist_ok=True)
        with open(splits_cache, "w") as f:
            json.dump(splits, f, indent=2)

    return train_data, val_data, test_data


def build_dataloaders(
    data_dir: str,
    splits_cache: str,
    batch_size: int = 32,
    num_workers: int = 0,
    train_mode: str = "train_standard"
):
    """Builds PyTorch DataLoaders for train, val, and test."""
    train_split, val_split, test_split = get_data_splits(data_dir, splits_cache)

    train_ds = CRCDataset(train_split["files"], train_split["labels"], transform_mode=train_mode)
    val_ds = CRCDataset(val_split["files"], val_split["labels"], transform_mode="eval")
    test_ds = CRCDataset(test_split["files"], test_split["labels"], transform_mode="eval")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    return train_loader, val_loader, test_loader
