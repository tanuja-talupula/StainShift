"""
Tests for CLI dry-run and argument verification flags.
"""

import subprocess
import sys
from pathlib import Path


def test_train_cli_dry_run(synthetic_dataset_dir, tmp_path):
    """Tests that src/train.py --dry-run completes successfully without starting training."""
    cmd = [
        sys.executable,
        "-m",
        "src.train",
        "--data_dir", str(synthetic_dataset_dir),
        "--output_dir", str(tmp_path),
        "--dry-run",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "[DRY-RUN]" in res.stdout


def test_evaluate_cli_dry_run(synthetic_dataset_dir, tmp_path):
    """Tests that src/evaluate.py --dry-run verifies paths without executing inference."""
    dummy_ckpt = tmp_path / "dummy.pth"
    dummy_ckpt.write_text("placeholder")

    cmd = [
        sys.executable,
        "-m",
        "src.evaluate",
        "--checkpoint", str(dummy_ckpt),
        "--data_dir", str(synthetic_dataset_dir),
        "--dry-run",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "[DRY-RUN]" in res.stdout


def test_run_experiments_cli_dry_run(synthetic_dataset_dir, tmp_path):
    """Tests that run_experiments.py --dry-run validates configuration successfully."""
    cmd = [
        sys.executable,
        "run_experiments.py",
        "--data_dir", str(synthetic_dataset_dir),
        "--models_dir", str(tmp_path / "models"),
        "--exp_dir", str(tmp_path / "exp"),
        "--dry-run",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "[DRY-RUN]" in res.stdout
