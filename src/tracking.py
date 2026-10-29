"""
StainShift: Optional MLflow Experiment Tracking
Provides structured logging for custom PyTorch training loops, multi-condition
stain-shift evaluations, and artifact generation.

Keeps application fully functional when MLflow is disabled or not installed.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional, Union

# Opt-in to allow file-store while recommending SQLite backend
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

logger = logging.getLogger(__name__)

# Check if mlflow is installed
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MLFLOW_AVAILABLE = False


def get_git_commit(repo_dir: Optional[Union[str, Path]] = None) -> str:
    """Retrieves current Git commit SHA without throwing exceptions."""
    try:
        cmd = ["git", "rev-parse", "HEAD"]
        cwd = str(repo_dir) if repo_dir else str(Path(__file__).resolve().parent.parent)
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown_commit"


class MLflowTracker:
    """
    Lightweight, manual experiment tracker wrapper around MLflow.
    Guarantees:
    - Zero failures when MLflow is disabled or uninstalled.
    - Explicit run labeling ('smoke_test' vs 'full_experiment').
    - Large artifacts and checkpoints are NEVER uploaded by default.
    - Per-condition evaluation metrics are isolated with distinct metric keys.
    """

    def __init__(
        self,
        enabled: bool = False,
        tracking_uri: Optional[str] = None,
        artifact_location: Optional[str] = None,
        experiment_name: str = "stainshift_benchmark",
        run_name: Optional[str] = None,
        run_type: str = "smoke_test",
        tags: Optional[Dict[str, Any]] = None,
        log_checkpoints: bool = False,
    ):
        self.enabled = bool(enabled and MLFLOW_AVAILABLE)
        self.tracking_uri = tracking_uri
        self.artifact_location = artifact_location
        self.experiment_name = experiment_name
        self.run_name = run_name
        self.run_type = run_type
        self.log_checkpoints = log_checkpoints
        self._active_run = None
        self._logged_params: Dict[str, Any] = {}

        if enabled and not MLFLOW_AVAILABLE:
            raise ImportError(
                "MLflow tracking was explicitly requested via --use_mlflow, but the 'mlflow' "
                "package is not installed. Install it with 'pip install mlflow' or run without --use_mlflow."
            )

        self.initial_tags = {
            "run_type": run_type,
            "git_commit": get_git_commit(),
            **(tags or {})
        }

    def __enter__(self) -> MLflowTracker:
        self.start_run()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.end_run(status="FAILED" if exc_type else "FINISHED")

    def start_run(self, run_name: Optional[str] = None, tags: Optional[Dict[str, Any]] = None) -> None:
        if not self.enabled:
            return

        if self.tracking_uri:
            mlflow.set_tracking_uri(self.tracking_uri)

        exp = mlflow.get_experiment_by_name(self.experiment_name)
        if exp is None:
            if self.artifact_location:
                mlflow.create_experiment(self.experiment_name, artifact_location=self.artifact_location)
                mlflow.set_experiment(self.experiment_name)
            else:
                mlflow.set_experiment(self.experiment_name)
        else:
            mlflow.set_experiment(self.experiment_name)

        combined_tags = dict(self.initial_tags)
        if tags:
            combined_tags.update(tags)

        name = run_name or self.run_name
        self._active_run = mlflow.start_run(run_name=name, tags=combined_tags)
        logger.info(
            "Started MLflow run '%s' (id: %s) in experiment '%s'",
            name, self._active_run.info.run_id, self.experiment_name
        )

    @property
    def run_id(self) -> Optional[str]:
        if self._active_run is not None:
            return self._active_run.info.run_id
        return None

    def end_run(self, status: str = "FINISHED") -> None:
        if not self.enabled or not self._active_run:
            return
        mlflow.end_run(status=status)
        self._active_run = None

    def log_params(self, params: Dict[str, Any], prefix: Optional[str] = None) -> None:
        if not self.enabled or not self._active_run:
            return
        # Flatten and stringify complex types for MLflow compatibility
        clean_params = {}
        for k, v in params.items():
            key = f"{prefix}_{k}" if prefix else str(k)
            val = "None" if v is None else (v if isinstance(v, (int, float, str, bool)) else str(v)[:250])
            if key in self._logged_params:
                if self._logged_params[key] == val:
                    continue
                key = f"{key}_val"
            clean_params[key] = val
            self._logged_params[key] = val

        if clean_params:
            mlflow.log_params(clean_params)

    def log_epoch_metrics(
        self,
        epoch: int,
        train_metrics: Dict[str, float],
        val_metrics: Dict[str, float],
        prefix: Optional[str] = None,
    ) -> None:
        """Logs train and val metrics for a training epoch."""
        if not self.enabled or not self._active_run:
            return
        pfx = f"{prefix}/" if prefix else ""
        metrics = {}
        for k, v in train_metrics.items():
            metrics[f"{pfx}train/{k}"] = float(v)
        for k, v in val_metrics.items():
            metrics[f"{pfx}val/{k}"] = float(v)
        mlflow.log_metrics(metrics, step=int(epoch))

    def log_eval_metrics(
        self,
        profile_name: str,
        metrics: Dict[str, Any],
        step: Optional[int] = None,
        prefix: Optional[str] = None,
    ) -> None:
        """
        Logs evaluation metrics under a dedicated stain profile prefix.
        Keeps original, reconstruction_only, and shift conditions distinct.
        """
        if not self.enabled or not self._active_run:
            return
        pfx = f"{prefix}/" if prefix else ""
        clean_metrics = {}
        scalar_keys = [
            "accuracy", "macro_f1", "mean_confidence", "delta_acc_pct",
            "delta_f1", "prediction_flip_rate_pct"
        ]
        for key in scalar_keys:
            if key in metrics and metrics[key] is not None:
                clean_metrics[f"{pfx}eval_{profile_name}/{key}"] = float(metrics[key])

        if "transform_stats" in metrics:
            stats = metrics["transform_stats"]
            clean_metrics[f"{pfx}eval_{profile_name}/failures"] = int(stats.get("failures", 0))
            clean_metrics[f"{pfx}eval_{profile_name}/attempts"] = int(stats.get("attempts", 0))

        mlflow.log_metrics(clean_metrics, step=step)

    def log_dict_artifact(
        self,
        data: Dict[str, Any],
        artifact_filename: str,
        artifact_path: Optional[str] = None
    ) -> None:
        """Saves a dictionary as a JSON artifact in MLflow run storage."""
        if not self.enabled:
            return
        import tempfile
        fname = Path(artifact_filename).name
        dir_path = artifact_path or (
            str(Path(artifact_filename).parent) if Path(artifact_filename).parent != Path(".") else None
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_file = Path(tmpdir) / fname
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            mlflow.log_artifact(str(tmp_file), artifact_path=dir_path)

    def log_artifact(self, local_path: Union[str, Path], artifact_path: Optional[str] = None) -> None:
        """Logs a local file as an MLflow artifact."""
        if not self.enabled:
            return
        p = Path(local_path)
        if p.is_file():
            mlflow.log_artifact(str(p), artifact_path=artifact_path)

    def log_checkpoint(self, checkpoint_path: Union[str, Path]) -> None:
        """
        Logs a trained model checkpoint file ONLY if explicit permission is granted
        via log_checkpoints=True. Avoids large storage bloat by default.
        """
        if not self.enabled or not self.log_checkpoints:
            return
        p = Path(checkpoint_path)
        if p.is_file():
            logger.info("Logging model checkpoint artifact to MLflow: %s", p.name)
            mlflow.log_artifact(str(p), artifact_path="checkpoints")
