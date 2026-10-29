"""
StainShift: Training Pipeline
Trains a histopathology patch classifier with standard or stain-augmented pipelines.
"""

import os
import sys
import time
import argparse
import json
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from sklearn.metrics import f1_score, accuracy_score

from .models import get_model, CLASS_NAMES
from .dataset import build_dataloaders, get_data_splits, CRCDataset


def train_epoch(model, dataloader, criterion, optimizer, device):
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

    epoch_loss = running_loss / len(dataloader.dataset)
    epoch_acc = accuracy_score(all_targets, all_preds)
    epoch_f1 = f1_score(all_targets, all_preds, average="macro", zero_division=0)
    return epoch_loss, epoch_acc, epoch_f1


@torch.no_grad()
def evaluate_epoch(model, dataloader, criterion, device):
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

    val_loss = running_loss / len(dataloader.dataset)
    val_acc = accuracy_score(all_targets, all_preds)
    val_f1 = f1_score(all_targets, all_preds, average="macro", zero_division=0)
    return val_loss, val_acc, val_f1


def run_training(
    data_dir: str,
    splits_cache: str,
    output_dir: str,
    model_name: str = "baseline",
    train_mode: str = "train_standard",
    arch: str = "mobilenet_v3_small",
    epochs: int = 5,
    batch_size: int = 32,
    lr: float = 3e-4,
    device: str = "cpu"
):
    print(f"=== Starting Training: {model_name} (Mode: {train_mode}, Arch: {arch}, Device: {device}) ===")
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device(device)

    train_loader, val_loader, test_loader = build_dataloaders(
        data_dir=data_dir,
        splits_cache=splits_cache,
        batch_size=batch_size,
        train_mode=train_mode
    )

    print(f"Dataset summary: Train={len(train_loader.dataset)}, Val={len(val_loader.dataset)}, Test={len(test_loader.dataset)}")

    model = get_model(arch=arch, pretrained=True, num_classes=len(CLASS_NAMES)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs)

    history = {"train_loss": [], "train_acc": [], "train_f1": [], "val_loss": [], "val_acc": [], "val_f1": []}
    best_val_f1 = 0.0
    best_model_path = os.path.join(output_dir, f"{model_name}.pth")

    start_time = time.time()
    for epoch in range(1, epochs + 1):
        t0 = time.time()
        tr_loss, tr_acc, tr_f1 = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc, val_f1 = evaluate_epoch(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        history["train_loss"].append(tr_loss)
        history["train_acc"].append(tr_acc)
        history["train_f1"].append(tr_f1)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        history["val_f1"].append(val_f1)

        print(f"Epoch [{epoch}/{epochs}] ({elapsed:.1f}s) - "
              f"Train Loss: {tr_loss:.4f}, Acc: {tr_acc*100:.2f}%, F1: {tr_f1:.4f} | "
              f"Val Loss: {val_loss:.4f}, Acc: {val_acc*100:.2f}%, F1: {val_f1:.4f}")

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_acc": val_acc,
                "val_f1": val_f1,
                "arch": arch,
                "train_mode": train_mode
            }, best_model_path)
            print(f"  --> Saved new best checkpoint to {best_model_path} (Val F1: {val_f1:.4f})")

    total_time = time.time() - start_time
    print(f"Training completed in {total_time/60:.2f} minutes. Best Val F1: {best_val_f1:.4f}")

    # Save history
    history_path = os.path.join(output_dir, f"{model_name}_history.json")
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    return best_model_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default=r"C:\Users\HP\.gemini\antigravity\scratch\stainshift\data\CRC-VAL-HE-7K-png")
    parser.add_argument("--splits_cache", type=str, default=r"C:\Users\HP\.gemini\antigravity\scratch\stainshift\data\splits.json")
    parser.add_argument("--output_dir", type=str, default=r"C:\Users\HP\.gemini\antigravity\scratch\stainshift\models")
    parser.add_argument("--model_name", type=str, default="baseline")
    parser.add_argument("--train_mode", type=str, default="train_standard", choices=["train_standard", "train_stain_augmented"])
    parser.add_argument("--arch", type=str, default="mobilenet_v3_small")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-4)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    run_training(
        data_dir=args.data_dir,
        splits_cache=args.splits_cache,
        output_dir=args.output_dir,
        model_name=args.model_name,
        train_mode=args.train_mode,
        arch=args.arch,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        device=device
    )
