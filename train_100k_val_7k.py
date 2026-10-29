"""
StainShift: Train on NCT-CRC-HE-100K-NONORM and Validate on CRC-VAL-HE-7K
Implements the multi-center digital pathology benchmark (Kather et al., PLOS Medicine 2019).
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image
from sklearn.metrics import classification_report, accuracy_score, f1_score
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as T

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset import IMAGENET_MEAN, IMAGENET_STD
from src.models import CLASS_NAMES, CLASS_DESCRIPTIONS, get_model, save_checkpoint

logger = logging.getLogger(__name__)


class HistopathologyFolderDataset(Dataset):
    """
    Loads patches from a directory containing files formatted as <CLASS>-<ID>.png.
    Uses an isolated RNG generator to prevent deterministic index collisions across classes.
    """

    def __init__(
        self,
        root_dir: Union[str, Path],
        is_train: bool = False,
        max_samples_per_class: Optional[int] = None,
        seed: int = 42,
    ):
        self.root_dir = Path(root_dir)
        self.is_train = is_train

        class_to_idx = {name: i for i, name in enumerate(CLASS_NAMES)}
        self.samples: List[Tuple[str, int]] = []

        all_files = sorted(self.root_dir.glob("*.png"))
        if not all_files:
            raise FileNotFoundError(f"No PNG files found in {self.root_dir}")

        by_class: Dict[str, List[Path]] = {name: [] for name in CLASS_NAMES}
        for fpath in all_files:
            cname = fpath.stem.split("-")[0]
            if cname in class_to_idx:
                by_class[cname].append(fpath)

        # Use an isolated random generator instantiated once
        rng = np.random.default_rng(seed)

        for cname in sorted(by_class.keys()):
            items = by_class[cname]
            if max_samples_per_class and len(items) > max_samples_per_class:
                indices = rng.choice(len(items), max_samples_per_class, replace=False)
                items = [items[i] for i in indices]
            for p in items:
                self.samples.append((str(p), class_to_idx[cname]))

        print(f"Loaded {len(self.samples)} images from {self.root_dir} across {len(CLASS_NAMES)} classes.")

        if is_train:
            self.transform = T.Compose([
                T.RandomHorizontalFlip(),
                T.RandomVerticalFlip(),
                T.ToTensor(),
                T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
            ])
        else:
            self.transform = T.Compose([
                T.ToTensor(),
                T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
            ])

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, str]:
        path, label = self.samples[idx]
        with Image.open(path) as img:
            img = img.convert("RGB")
        tensor = self.transform(img)
        return tensor, label, path


def train_one_epoch(model, dataloader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    all_preds, all_targets = [], []

    for images, targets, _ in dataloader:
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
    epoch_acc = accuracy_score(all_targets, all_preds)
    epoch_f1 = f1_score(all_targets, all_preds, average="macro", zero_division=0)
    return epoch_loss, epoch_acc, epoch_f1


@torch.no_grad()
def evaluate_cohort(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    all_preds, all_targets = [], []

    for images, targets, _ in dataloader:
        images, targets = images.to(device), targets.to(device)
        outputs = model(images)
        loss = criterion(outputs, targets)

        running_loss += loss.item() * images.size(0)
        preds = torch.argmax(outputs, dim=1).cpu().numpy()
        all_preds.extend(preds)
        all_targets.extend(targets.cpu().numpy())

    val_loss = running_loss / max(len(dataloader.dataset), 1)
    val_acc = accuracy_score(all_targets, all_preds)
    val_f1 = f1_score(all_targets, all_preds, average="macro", zero_division=0)
    report = classification_report(
        all_targets,
        all_preds,
        labels=list(range(len(CLASS_NAMES))),
        target_names=CLASS_NAMES,
        output_dict=True,
        zero_division=0
    )

    return val_loss, val_acc, val_f1, report


def main() -> None:
    parser = argparse.ArgumentParser(description="StainShift 100K Training and 7K Validation")
    parser.add_argument("--train_dir", type=str, default="data/NCT-CRC-HE-100K-NONORM-png")
    parser.add_argument("--val_dir", type=str, default="data/CRC-VAL-HE-7K-png")
    parser.add_argument("--output_dir", type=str, default="models")
    parser.add_argument("--exp_dir", type=str, default="experiments")
    parser.add_argument("--max_train_per_class", type=int, default=None, help="Subset per class for quick testing")
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--selection_protocol",
        type=str,
        default="external_val_selection",
        choices=["external_val_selection", "internal_dev_split"],
        help="Protocol for checkpoint selection vs untouched external testing"
    )
    parser.add_argument("--output_name", type=str, default="model_100k_nonorm")
    parser.add_argument("--dry-run", action="store_true", help="Validate setup without executing training")
    args = parser.parse_args()

    train_dir = Path(args.train_dir)
    val_dir = Path(args.val_dir)
    output_dir = Path(args.output_dir)
    exp_dir = Path(args.exp_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    exp_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Training on {train_dir.name} | Selection Protocol: {args.selection_protocol} ===")

    if args.dry_run:
        print("[DRY-RUN] Validating directories and parameters...")
        print(f"  Train dir: {train_dir} (Exists: {train_dir.is_dir()})")
        print(f"  Val dir: {val_dir} (Exists: {val_dir.is_dir()})")
        print(f"  Selection protocol: {args.selection_protocol}")
        print("[DRY-RUN] Validation complete.")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Build validation set
    val_dataset = HistopathologyFolderDataset(val_dir, is_train=False, seed=args.seed)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)

    # Build train set
    train_dataset = HistopathologyFolderDataset(
        train_dir,
        is_train=True,
        max_samples_per_class=args.max_train_per_class,
        seed=args.seed
    )
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)

    model = get_model(arch="mobilenet_v3_small", pretrained=True, num_classes=len(CLASS_NAMES)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(args.epochs, 1))

    save_path = output_dir / f"{args.output_name}.pth"
    best_val_f1 = -1.0
    best_report = None
    best_acc = 0.0

    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        print(f"\n--- Epoch [{epoch}/{args.epochs}] ---")
        tr_loss, tr_acc, tr_f1 = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc, val_f1, report = evaluate_cohort(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        print(f"Epoch [{epoch}/{args.epochs}] Completed in {elapsed/60:.2f}m")
        print(f"  Training ({train_dir.name}): Loss={tr_loss:.4f}, Acc={tr_acc*100:.2f}%, Macro F1={tr_f1:.4f}")
        print(f"  Validation ({val_dir.name}): Loss={val_loss:.4f}, Acc={val_acc*100:.2f}%, Macro F1={val_f1:.4f}")

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_acc = val_acc
            best_report = report
            save_checkpoint(
                model=model,
                save_path=save_path,
                architecture="mobilenet_v3_small",
                class_names=CLASS_NAMES,
                class_to_idx={name: i for i, name in enumerate(CLASS_NAMES)},
                epoch=epoch,
                metrics={"val_loss": val_loss, "val_acc": val_acc, "val_f1": val_f1},
                train_mode="train_standard",
                seed=args.seed,
                extra={
                    "selection_protocol": args.selection_protocol,
                    "validation_cohort": val_dir.name,
                    "warning": (
                        "External cohort was used for model selection; "
                        "this cohort cannot be considered an untouched final test."
                        if args.selection_protocol == "external_val_selection" else "Internal development validation split."
                    )
                }
            )
            print(f"  --> Saved new best checkpoint to {save_path} (Val F1: {val_f1:.4f})")

    # Final summary report
    print("\n=================================================================")
    print(f" VALIDATION PERFORMANCE SUMMARY (Protocol: {args.selection_protocol})")
    print("=================================================================")
    if best_report:
        print(f"{'Class':<8} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}")
        print("-" * 55)
        for cname in CLASS_NAMES:
            c_p = best_report[cname]["precision"]
            c_r = best_report[cname]["recall"]
            c_f1 = best_report[cname]["f1-score"]
            c_sup = int(best_report[cname]["support"])
            print(f"{cname:<8} | {c_p:>9.4f}  | {c_r:>9.4f}  | {c_f1:>9.4f}  | {c_sup:>7}")
        print("-" * 55)
        print(f"ACCURACY: {best_acc*100:.2f}% | MACRO F1: {best_val_f1:.4f}")

    results_json = exp_dir / f"{args.output_name}_results.json"
    with open(results_json, "w", encoding="utf-8") as f:
        json.dump({
            "selection_protocol": args.selection_protocol,
            "val_acc": best_acc,
            "val_f1": best_val_f1,
            "report": best_report,
            "note": (
                "External validation cohort used for model selection. Not an untouched test set."
                if args.selection_protocol == "external_val_selection" else "Standard internal validation."
            )
        }, f, indent=2)


if __name__ == "__main__":
    main()
