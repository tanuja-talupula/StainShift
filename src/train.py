"""
StainShift: Training Pipeline
Trains a histopathology patch classifier with standard or stain-augmented pipelines.
Includes optional MLflow experiment tracking.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from contextlib import nullcontext
from pathlib import Path
import random
import time
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from sklearn.metrics import accuracy_score, f1_score
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

from .dataset import build_dataloaders
from .models import CLASS_NAMES, get_model, save_checkpoint
from .tracking import MLflowTracker

logger = logging.getLogger(__name__)


def set_seed(seed: int) -> None:
    """Sets random seeds across Python, NumPy, and PyTorch for reproducible runs."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train_epoch(
    model: nn.Module,
    dataloader: Any,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device
) -> Tuple[float, float, float]:
    """Trains for a single epoch and returns (loss, accuracy, macro_f1)."""
    model.train()
    running_loss = 0.0
    all_preds = []
    all_targets = []

    for batch_idx, (images, targets, _) in enumerate(dataloader):
        images, targets = images.to(device), targets.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        preds = torch.argmax(outputs, dim=1).detach().cpu().numpy()
        all_preds.extend(preds)
        all_targets.extend(targets.cpu().numpy())

    epoch_loss = running_loss / max(len(dataloader.dataset), 1)
    epoch_acc = float(accuracy_score(all_targets, all_preds))
    epoch_f1 = float(f1_score(all_targets, all_preds, average="macro", zero_division=0))
    return epoch_loss, epoch_acc, epoch_f1


@torch.no_grad()
def evaluate_epoch(
    model: nn.Module,
    dataloader: Any,
    criterion: nn.Module,
    device: torch.device
) -> Tuple[float, float, float]:
    """Evaluates on validation data and returns (loss, accuracy, macro_f1)."""
    model.eval()
    running_loss = 0.0
    all_preds = []
    all_targets = []

    for images, targets, _ in dataloader:
        images, targets = images.to(device), targets.to(device)
        outputs = model(images)
        loss = criterion(outputs, targets)

        running_loss += loss.item() * images.size(0)
        preds = torch.argmax(outputs, dim=1).cpu().numpy()
        all_preds.extend(preds)
        all_targets.extend(targets.cpu().numpy())

    val_loss = running_loss / max(len(dataloader.dataset), 1)
    val_acc = float(accuracy_score(all_targets, all_preds))
    val_f1 = float(f1_score(all_targets, all_preds, average="macro", zero_division=0))
    return val_loss, val_acc, val_f1


def run_training(
    data_dir: Union[str, Path],
    splits_cache: Optional[Union[str, Path]] = None,
    output_dir: Union[str, Path] = "models",
    model_name: str = "baseline",
    train_mode: str = "train_standard",
    arch: str = "mobilenet_v3_small",
    pretrained: bool = True,
    epochs: int = 5,
    batch_size: int = 32,
    lr: float = 3e-4,
    device: str = "cpu",
    seed: int = 42,
    dry_run: bool = False,
    max_samples_per_class: Optional[int] = None,
    tracker: Optional[MLflowTracker] = None,
    log_models_to_mlflow: bool = False,
) -> Path:
    """
    Executes model training with complete reproducibility metadata.
    Supports optional MLflow tracking.
    """
    data_path = Path(data_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    best_model_path = out_path / f"{model_name}.pth"

    print(f"=== Starting Training: {model_name} (Mode: {train_mode}, Arch: {arch}, Device: {device}, Seed: {seed}) ===")

    if dry_run:
        print("[DRY-RUN] Verifying dataset and arguments without executing training.")
        if not data_path.is_dir():
            raise FileNotFoundError(f"Dataset directory not found: {data_path}")
        print(f"[DRY-RUN] Output checkpoint target: {best_model_path}")
        return best_model_path

    if tracker and tracker.enabled:
        tracker.log_params({
            "model_name": model_name,
            "architecture": arch,
            "pretrained": pretrained,
            "train_mode": train_mode,
            "epochs": epochs,
            "batch_size": batch_size,
            "lr": lr,
            "seed": seed,
            "device": device,
            "data_dir": str(data_path),
            "splits_cache": str(splits_cache) if splits_cache else "None",
        }, prefix=model_name)

    set_seed(seed)
    dev = torch.device(device)

    train_loader, val_loader, test_loader = build_dataloaders(
        data_dir=data_path,
        splits_cache=splits_cache,
        batch_size=batch_size,
        train_mode=train_mode,
        seed=seed,
        max_samples_per_class=max_samples_per_class,
    )

    print(f"Dataset summary: Train={len(train_loader.dataset)}, Val={len(val_loader.dataset)}, Test={len(test_loader.dataset)}")

    model = get_model(arch=arch, pretrained=pretrained, num_classes=len(CLASS_NAMES)).to(dev)
    criterion = nn.CrossEntropyLoss()
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=max(epochs, 1))

    history: Dict[str, list] = {
        "train_loss": [], "train_acc": [], "train_f1": [],
        "val_loss": [], "val_acc": [], "val_f1": []
    }

    # Initialize at -1.0 so epoch 1 is always saved even if metric is 0.0
    best_val_f1 = -1.0
    best_epoch = 0
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        tr_loss, tr_acc, tr_f1 = train_epoch(model, train_loader, criterion, optimizer, dev)
        val_loss, val_acc, val_f1 = evaluate_epoch(model, val_loader, criterion, dev)
        scheduler.step()
        elapsed = time.time() - t0

        history["train_loss"].append(tr_loss)
        history["train_acc"].append(tr_acc)
        history["train_f1"].append(tr_f1)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        history["val_f1"].append(val_f1)

        print(
            f"Epoch [{epoch}/{epochs}] ({elapsed:.1f}s) - "
            f"Train Loss: {tr_loss:.4f}, Acc: {tr_acc*100:.2f}%, F1: {tr_f1:.4f} | "
            f"Val Loss: {val_loss:.4f}, Acc: {val_acc*100:.2f}%, F1: {val_f1:.4f}"
        )

        if tracker and tracker.enabled:
            tracker.log_epoch_metrics(
                epoch=epoch,
                train_metrics={"loss": tr_loss, "accuracy": tr_acc, "macro_f1": tr_f1},
                val_metrics={"loss": val_loss, "accuracy": val_acc, "macro_f1": val_f1},
                prefix=model_name,
            )

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_epoch = epoch
            save_checkpoint(
                model=model,
                save_path=best_model_path,
                architecture=arch,
                class_names=CLASS_NAMES,
                class_to_idx={name: i for i, name in enumerate(CLASS_NAMES)},
                epoch=epoch,
                metrics={"val_loss": val_loss, "val_acc": val_acc, "val_f1": val_f1},
                train_mode=train_mode,
                seed=seed,
                split_info={"data_dir": str(data_path), "splits_cache": str(splits_cache) if splits_cache else None},
            )
            print(f"  --> Saved new best checkpoint to {best_model_path} (Val F1: {val_f1:.4f})")

    total_time = time.time() - start_time
    print(f"Training completed in {total_time/60:.2f} minutes. Best Val F1: {best_val_f1:.4f} at epoch {best_epoch}")

    # Save training history
    history_path = out_path / f"{model_name}_history.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    if tracker and tracker.enabled:
        tracker.log_params({
            f"{model_name}_best_epoch": best_epoch,
            f"{model_name}_best_val_f1": round(best_val_f1, 4),
            f"{model_name}_selection_rule": "highest_validation_macro_f1",
            f"{model_name}_training_elapsed_seconds": round(total_time, 2),
        })
        tracker.log_artifact(history_path)
        if log_models_to_mlflow:
            tracker.log_checkpoint(best_model_path)


    return best_model_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StainShift Model Training")
    parser.add_argument("--data_dir", type=str, default="data/CRC-VAL-HE-7K-png", help="Path to patch dataset directory")
    parser.add_argument("--splits_cache", type=str, default="data/splits.json", help="Path to splits JSON file")
    parser.add_argument("--output_dir", type=str, default="models", help="Output directory for checkpoints")
    parser.add_argument("--model_name", type=str, default="baseline")
    parser.add_argument(
        "--train_mode",
        type=str,
        default="train_standard",
        choices=["train_standard", "train_stain_augmented", "stain_augmented"],
        help="Augmentation mode"
    )
    parser.add_argument("--arch", type=str, default="mobilenet_v3_small", choices=["mobilenet_v3_small", "resnet18"])
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--max_samples_per_class", type=int, default=None, help="Limit samples per class for bounded smoke tests")
    parser.add_argument("--no_pretrained", action="store_true", help="Initialize model with random weights instead of pretrained torchvision weights")
    parser.add_argument("--dry-run", action="store_true", help="Validate setup without training")
    # MLflow arguments
    parser.add_argument("--use_mlflow", action="store_true", help="Enable MLflow experiment tracking")
    parser.add_argument("--mlflow_tracking_uri", type=str, default=os.getenv("MLFLOW_TRACKING_URI"), help="MLflow tracking URI")
    parser.add_argument("--mlflow_artifact_root", type=str, default=os.getenv("MLFLOW_ARTIFACT_ROOT"), help="MLflow artifact storage root directory")
    parser.add_argument("--mlflow_experiment_name", type=str, default=os.getenv("MLFLOW_EXPERIMENT_NAME", "stainshift_benchmark"), help="MLflow experiment name")
    parser.add_argument("--run_type", type=str, default="smoke_test", choices=["smoke_test", "full_experiment"], help="Label run as smoke_test or full_experiment")
    parser.add_argument("--log_models_to_mlflow", action="store_true", help="Explicitly log checkpoint weights to MLflow")
    args = parser.parse_args()

    tracker = None
    if args.use_mlflow:
        tracker = MLflowTracker(
            enabled=True,
            tracking_uri=args.mlflow_tracking_uri,
            artifact_location=args.mlflow_artifact_root,
            experiment_name=args.mlflow_experiment_name,
            run_name=f"train_{args.model_name}",
            run_type=args.run_type,
            log_checkpoints=args.log_models_to_mlflow,
        )

    with tracker if tracker else nullcontext():
        run_training(
            data_dir=args.data_dir,
            splits_cache=args.splits_cache,
            output_dir=args.output_dir,
            model_name=args.model_name,
            train_mode=args.train_mode,
            arch=args.arch,
            pretrained=not args.no_pretrained,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            device=args.device,
            seed=args.seed,
            dry_run=args.dry_run,
            max_samples_per_class=args.max_samples_per_class,
            tracker=tracker,
            log_models_to_mlflow=args.log_models_to_mlflow,
        )
