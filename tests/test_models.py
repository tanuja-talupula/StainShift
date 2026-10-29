"""
Tests for model construction, checkpoint metadata provenance, and safe loading.
"""

from pathlib import Path
import pytest
import torch
import torch.nn as nn

from src.models import (
    CLASS_NAMES,
    NUM_CLASSES,
    get_model,
    load_checkpoint,
    save_checkpoint,
)


def test_no_import_side_effects():
    """Proves that importing src.models does not set Windows-specific TORCH_HOME."""
    import src.models as m
    import os
    torch_home = os.environ.get("TORCH_HOME", "")
    assert "C:\\Users" not in torch_home
    assert not Path("C:/Users").exists()


def test_get_model_architectures():
    """Tests model construction for supported backbones."""
    m1 = get_model("mobilenet_v3_small", pretrained=False, num_classes=NUM_CLASSES)
    assert isinstance(m1, nn.Module)

    m2 = get_model("resnet18", pretrained=False, num_classes=NUM_CLASSES)
    assert isinstance(m2, nn.Module)

    with pytest.raises(ValueError, match="Unsupported architecture"):
        get_model("vgg16_unknown", pretrained=False)


def test_save_and_load_checkpoint_roundtrip(tmp_path):
    """Tests saving and loading a checkpoint with full provenance metadata."""
    model = get_model("mobilenet_v3_small", pretrained=False, num_classes=NUM_CLASSES)
    ckpt_path = tmp_path / "test_model.pth"

    save_checkpoint(
        model=model,
        save_path=ckpt_path,
        architecture="mobilenet_v3_small",
        class_names=CLASS_NAMES,
        class_to_idx={name: i for i, name in enumerate(CLASS_NAMES)},
        epoch=2,
        metrics={"val_loss": 0.35, "val_acc": 0.88, "val_f1": 0.87},
        train_mode="train_stain_augmented",
        seed=42,
    )

    loaded_model, meta = load_checkpoint(
        ckpt_path,
        expected_arch="mobilenet_v3_small",
        expected_classes=CLASS_NAMES,
        device="cpu",
    )
    assert isinstance(loaded_model, nn.Module)
    assert meta["provenance"] == "verified_run"
    assert meta["architecture"] == "mobilenet_v3_small"
    assert meta["epoch"] == 2
    assert meta["train_mode"] == "train_stain_augmented"
    assert meta["seed"] == 42


def test_load_checkpoint_missing_file_raises_filenotfound():
    """Proves that missing checkpoints raise FileNotFoundError and never return random weights."""
    missing_path = Path("/tmp/definitely_missing_checkpoint_12345.pth")
    with pytest.raises(FileNotFoundError, match="Checkpoint file does not exist"):
        load_checkpoint(missing_path)


def test_load_checkpoint_architecture_mismatch_raises_valueerror(tmp_path):
    """Proves that loading a checkpoint with mismatched architecture raises ValueError."""
    model = get_model("mobilenet_v3_small", pretrained=False, num_classes=NUM_CLASSES)
    ckpt_path = tmp_path / "test_mismatch.pth"

    save_checkpoint(
        model=model,
        save_path=ckpt_path,
        architecture="mobilenet_v3_small",
        class_names=CLASS_NAMES,
        class_to_idx={name: i for i, name in enumerate(CLASS_NAMES)},
        epoch=1,
        metrics={"val_f1": 0.8},
        train_mode="train_standard",
        seed=42,
    )

    with pytest.raises(ValueError, match="Checkpoint architecture mismatch"):
        load_checkpoint(
            ckpt_path,
            expected_arch="resnet18",
            device="cpu",
        )


def test_legacy_checkpoint_loading_policy(tmp_path):
    """Proves that legacy checkpoints require explicit allow_legacy=True."""
    model = get_model("mobilenet_v3_small", pretrained=False, num_classes=NUM_CLASSES)
    legacy_path = tmp_path / "legacy.pth"

    # Save bare legacy dict with only model_state_dict
    torch.save({"model_state_dict": model.state_dict(), "val_f1": 0.85}, legacy_path)

    # Without allow_legacy=True, it must fail
    with pytest.raises(ValueError, match="legacy format without provenance metadata"):
        load_checkpoint(legacy_path, expected_arch="mobilenet_v3_small", allow_legacy=False)

    # With allow_legacy=True and expected_arch, it succeeds with legacy provenance
    loaded_model, meta = load_checkpoint(
        legacy_path,
        expected_arch="mobilenet_v3_small",
        allow_legacy=True,
    )
    assert meta["provenance"] == "legacy_unverified"
    assert meta["architecture"] == "mobilenet_v3_small"
