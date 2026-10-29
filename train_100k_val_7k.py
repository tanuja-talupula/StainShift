"""
StainShift: Train on NCT-CRC-HE-100K-NONORM and Validate on CRC-VAL-HE-7K
Implements the multi-center digital pathology benchmark (Kather et al., PLOS Medicine 2019).
"""

import os
import sys
import glob
import time
import json
import argparse
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T
from sklearn.metrics import classification_report, accuracy_score, f1_score

BASE_DIR = r"C:\Users\HP\.gemini\antigravity\scratch\stainshift"
os.environ["TORCH_HOME"] = r"C:\Users\HP\.gemini\antigravity\scratch\torch_cache"
sys.path.append(BASE_DIR)

from src.models import get_model, CLASS_NAMES, CLASS_DESCRIPTIONS
from src.dataset import IMAGENET_MEAN, IMAGENET_STD


class HistopathologyFolderDataset(Dataset):
    """
    Loads patches from a directory containing files formatted as <CLASS>-<ID>.png.
    """

    def __init__(self, root_dir: str, is_train: bool = False, max_samples_per_class: int = None):
        self.root_dir = root_dir
        self.is_train = is_train

        class_to_idx = {name: i for i, name in enumerate(CLASS_NAMES)}
        self.samples = []

        all_files = glob.glob(os.path.join(root_dir, "*.png"))
        if not all_files:
            raise FileNotFoundError(f"No PNG files found in {root_dir}")

        by_class = {name: [] for name in CLASS_NAMES}
        for fpath in all_files:
            fname = os.path.basename(fpath)
            cname = fname.split("-")[0]
            if cname in class_to_idx:
                by_class[cname].append((fpath, class_to_idx[cname]))

        for cname, items in by_class.items():
            if max_samples_per_class and len(items) > max_samples_per_class:
                # Random sample
                np.random.seed(42)
                indices = np.random.choice(len(items), max_samples_per_class, replace=False)
                items = [items[i] for i in indices]
            self.samples.extend(items)

        print(f"Loaded {len(self.samples)} images from {root_dir} across {len(CLASS_NAMES)} classes.")

        self.tensor_transform = T.Compose([
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
        ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        fpath, label = self.samples[idx]
        with Image.open(fpath) as img:
            img = img.convert("RGB")

        if self.is_train:
            import random
            if random.random() > 0.5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if random.random() > 0.5:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            rot = random.choice([0, 90, 180, 270])
            if rot > 0:
                img = img.rotate(rot)

        tensor = self.tensor_transform(img)
        return tensor, label, fpath


def train_one_epoch(model, dataloader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    all_preds, all_targets = [], []

    t0 = time.time()
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

        if (batch_idx + 1) % 100 == 0 or (batch_idx + 1) == len(dataloader):
            batch_loss = running_loss / len(all_targets)
            batch_acc = accuracy_score(all_targets, all_preds)
            print(f"  Step [{batch_idx+1}/{len(dataloader)}] - Loss: {batch_loss:.4f}, Running Acc: {batch_acc*100:.2f}%")

    epoch_loss = running_loss / len(dataloader.dataset)
    epoch_acc = accuracy_score(all_targets, all_preds)
    epoch_f1 = f1_score(all_targets, all_preds, average="macro", zero_division=0)
    return epoch_loss, epoch_acc, epoch_f1


@torch.no_grad()
def validate_on_7k(model, dataloader, criterion, device):
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

    val_loss = running_loss / len(dataloader.dataset)
    val_acc = accuracy_score(all_targets, all_preds)
    val_f1 = f1_score(all_targets, all_preds, average="macro", zero_division=0)
    report = classification_report(all_targets, all_preds, target_names=CLASS_NAMES, output_dict=True, zero_division=0)

    return val_loss, val_acc, val_f1, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_dir", type=str, default=os.path.join(BASE_DIR, "data", "NCT-CRC-HE-100K-NONORM-png"))
    parser.add_argument("--val_dir", type=str, default=os.path.join(BASE_DIR, "data", "CRC-VAL-HE-7K-png"))
    parser.add_argument("--max_train_per_class", type=int, default=None, help="Optional subset (e.g. 2000 per class = 18K patches) for faster CPU training")
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--output_name", type=str, default="model_100k_nonorm")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"=== Training on NCT-CRC-HE-100K-NONORM | Validating on CRC-VAL-HE-7K ===")
    print(f"Device: {device}")

    # Build validation set (all 7,180 patches from CRC-VAL-HE-7K)
    val_dataset = HistopathologyFolderDataset(args.val_dir, is_train=False)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)

    # Build training set from NCT-CRC-HE-100K-NONORM
    train_dataset = HistopathologyFolderDataset(
        args.train_dir,
        is_train=True,
        max_samples_per_class=args.max_train_per_class
    )
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)

    # Initialize model
    model = get_model("mobilenet_v3_small", pretrained=True, num_classes=len(CLASS_NAMES)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_f1 = 0.0
    save_path = os.path.join(BASE_DIR, "models", f"{args.output_name}.pth")

    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        print(f"\n--- Epoch [{epoch}/{args.epochs}] ---")
        tr_loss, tr_acc, tr_f1 = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc, val_f1, report = validate_on_7k(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        print(f"Epoch [{epoch}/{args.epochs}] Completed in {elapsed/60:.2f}m")
        print(f"  Training (100K-NONORM): Loss={tr_loss:.4f}, Acc={tr_acc*100:.2f}%, Macro F1={tr_f1:.4f}")
        print(f"  Validation (CRC-VAL-7K): Loss={val_loss:.4f}, Acc={val_acc*100:.2f}%, Macro F1={val_f1:.4f}")

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_acc": val_acc,
                "val_f1": val_f1,
                "report": report
            }, save_path)
            print(f"  --> Saved new best checkpoint to {save_path} (Val F1 on 7K: {val_f1:.4f})")

    # Output detailed per-class report on 7K validation set
    print("\n=================================================================")
    print("      FINAL VALIDATION PERFORMANCE ON CRC-VAL-HE-7K (50 PATIENTS) ")
    print("=================================================================")
    best_ckpt = torch.load(save_path, map_location=device)
    rep = best_ckpt["report"]
    print(f"{'Class':<8} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}")
    print("-" * 55)
    for cname in CLASS_NAMES:
        c_p = rep[cname]["precision"]
        c_r = rep[cname]["recall"]
        c_f1 = rep[cname]["f1-score"]
        c_sup = int(rep[cname]["support"])
        print(f"{cname:<8} | {c_p:>9.4f}  | {c_r:>9.4f}  | {c_f1:>9.4f}  | {c_sup:>7}")
    print("-" * 55)
    print(f"OVERALL ACCURACY: {best_ckpt['val_acc']*100:.2f}% | MACRO F1: {best_ckpt['val_f1']:.4f}")

    results_json = os.path.join(BASE_DIR, "experiments", f"{args.output_name}_results.json")
    with open(results_json, "w") as f:
        json.dump({"accuracy": best_ckpt["val_acc"], "macro_f1": best_ckpt["val_f1"], "report": rep}, f, indent=2)
    print(f"Results report saved to: {results_json}")


if __name__ == "__main__":
    main()
