"""
Shared test fixtures and synthetic image generators for StainShift test suite.
All fixtures are tiny, synthetic, and non-biomedical engineering artifacts.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator, Tuple

import numpy as np
from PIL import Image
import pytest

from src.models import CLASS_NAMES


@pytest.fixture
def synthetic_he_patch() -> np.ndarray:
    """
    Creates a small 64x64 synthetic RGB patch simulating typical H&E absorption
    (purple nuclei, pink cytoplasm/stroma, and white/glass background).
    """
    np.random.seed(42)
    img = np.full((64, 64, 3), 245, dtype=np.uint8)  # Background glass

    # Add pink stroma (rows 10-50, cols 10-50)
    img[10:55, 10:55] = [210, 130, 170]

    # Add deep purple/blue nuclei scattered inside stroma
    for r in range(15, 50, 6):
        for c in range(15, 50, 6):
            img[r:r+3, c:c+3] = [80, 40, 120]

    return img


@pytest.fixture
def synthetic_dataset_dir(synthetic_he_patch: np.ndarray) -> Generator[Path, None, None]:
    """
    Creates a temporary directory with a minimal set of synthetic PNG patches
    formatted as <CLASS>-<INDEX>.png for each of the 9 classes.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        img = Image.fromarray(synthetic_he_patch)

        for cname in CLASS_NAMES:
            for idx in range(12):  # 12 samples per class = 108 total samples
                fpath = tmp_path / f"{cname}-{idx:04d}.png"
                img.save(fpath)

        yield tmp_path
