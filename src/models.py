"""
StainShift: Model Architectures for Histopathology Patch Classification
Optimized for efficient training and inference on both CPU and GPU.
"""

import os
import torch
import torch.nn as nn
from torchvision import models

# Ensure torch cache uses the permitted scratch directory
SCRATCH_CACHE = r"C:\Users\HP\.gemini\antigravity\scratch\torch_cache"
os.makedirs(SCRATCH_CACHE, exist_ok=True)
os.environ.setdefault("TORCH_HOME", SCRATCH_CACHE)


CLASS_NAMES = [
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

CLASS_DESCRIPTIONS = {
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

NUM_CLASSES = len(CLASS_NAMES)


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
        raise ValueError(f"Unsupported architecture: {arch}")

    return model
