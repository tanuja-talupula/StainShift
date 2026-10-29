"""
Tests for optional MLflow experiment tracking.
Uses a temporary local file-based tracking store (file://...).
"""

import json
from pathlib import Path
import pytest

from src.tracking import MLflowTracker, get_git_commit

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False


def test_tracker_fails_loudly_when_enabled_without_mlflow(monkeypatch):
    """Proves that tracker fails loudly with an informative ImportError when enabled without mlflow."""
    monkeypatch.setattr("src.tracking.MLFLOW_AVAILABLE", False)
    with pytest.raises(ImportError, match="MLflow tracking was explicitly requested"):
        MLflowTracker(enabled=True)


def test_tracker_disabled_noop():
    """Proves that tracker is a safe no-op when enabled=False."""
    tracker = MLflowTracker(enabled=False)
    # None of these should throw
    tracker.start_run("test_run")
    tracker.log_params({"seed": 42})
    tracker.log_epoch_metrics(1, {"loss": 0.5}, {"loss": 0.6})
    tracker.log_eval_metrics("original", {"accuracy": 0.95})
    tracker.log_dict_artifact({"key": "val"}, "test.json")
    tracker.log_checkpoint("/tmp/nonexistent.pth")
    tracker.end_run()
    assert tracker._active_run is None


@pytest.mark.skipif(not MLFLOW_AVAILABLE, reason="mlflow is not installed")
def test_tracker_local_sqlite_store(tmp_path):
    """
    Proves that MLflowTracker logs parameters, per-epoch metrics,
    per-condition evaluation metrics, and artifacts to a local SQLite store.
    """
    db_file = tmp_path / "mlflow.db"
    tracking_uri = f"sqlite:///{db_file}"
    exp_name = "test_experiment"

    tracker = MLflowTracker(
        enabled=True,
        tracking_uri=tracking_uri,
        experiment_name=exp_name,
        run_name="smoke_test_run",
        run_type="smoke_test",
        tags={"custom_tag": "engineering_check"},
        log_checkpoints=False,
    )

    with tracker:
        tracker.log_params({
            "model_type": "mobilenet_v3_small",
            "seed": 42,
            "train_mode": "train_stain_augmented",
            "selection_protocol": "internal_dev_split",
            "provenance": "verified_run",
        })

        tracker.log_epoch_metrics(
            epoch=1,
            train_metrics={"loss": 0.45, "accuracy": 0.85, "macro_f1": 0.84},
            val_metrics={"loss": 0.48, "accuracy": 0.83, "macro_f1": 0.82},
        )

        tracker.log_eval_metrics(
            profile_name="original",
            metrics={"accuracy": 0.90, "macro_f1": 0.89, "delta_acc_pct": 0.0},
        )
        tracker.log_eval_metrics(
            profile_name="heavy_hematoxylin",
            metrics={"accuracy": 0.82, "macro_f1": 0.80, "delta_acc_pct": -8.0},
        )
        tracker.log_eval_metrics(
            profile_name="reconstruction_only",
            metrics={"accuracy": 0.88, "macro_f1": 0.87, "delta_acc_pct": -2.0},
        )

        dummy_report = {"TUM": {"precision": 0.92, "recall": 0.88, "f1-score": 0.90}}
        tracker.log_dict_artifact(dummy_report, "reports/classification_report_original.json")

        # Test that checkpoint is NOT logged by default
        dummy_ckpt = tmp_path / "model.pth"
        dummy_ckpt.write_text("weights")
        tracker.log_checkpoint(dummy_ckpt)

    # Verify run recorded in MLflow client
    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(exp_name)
    assert experiment is not None

    runs = client.search_runs(experiment_ids=[experiment.experiment_id])
    assert len(runs) == 1
    run = runs[0]

    # Verify tags
    assert run.data.tags["run_type"] == "smoke_test"
    assert "git_commit" in run.data.tags

    # Verify params
    assert run.data.params["model_type"] == "mobilenet_v3_small"
    assert run.data.params["seed"] == "42"
    assert run.data.params["selection_protocol"] == "internal_dev_split"

    # Verify metrics
    assert run.data.metrics["train/loss"] == 0.45
    assert run.data.metrics["val/loss"] == 0.48
    assert run.data.metrics["eval_original/accuracy"] == 0.90
    assert run.data.metrics["eval_heavy_hematoxylin/accuracy"] == 0.82
    assert run.data.metrics["eval_reconstruction_only/accuracy"] == 0.88

    # Verify artifacts: classification report logged, checkpoint NOT logged
    artifacts = [a.path for a in client.list_artifacts(run.info.run_id)]
    assert "reports" in artifacts
    assert "checkpoints" not in artifacts


@pytest.mark.skipif(not MLFLOW_AVAILABLE, reason="mlflow is not installed")
def test_tracker_explicit_checkpoint_logging(tmp_path):
    """Proves that checkpoints are uploaded only when log_checkpoints=True."""
    db_file = tmp_path / "mlflow_ckpt.db"
    tracking_uri = f"sqlite:///{db_file}"
    exp_name = "test_ckpt_experiment"

    tracker = MLflowTracker(
        enabled=True,
        tracking_uri=tracking_uri,
        experiment_name=exp_name,
        run_name="checkpoint_run",
        run_type="full_experiment",
        log_checkpoints=True,
    )

    dummy_ckpt = tmp_path / "explicit_model.pth"
    dummy_ckpt.write_text("explicit weights")

    with tracker:
        tracker.log_checkpoint(dummy_ckpt)

    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(exp_name)
    run = client.search_runs(experiment_ids=[experiment.experiment_id])[0]

    artifacts = [a.path for a in client.list_artifacts(run.info.run_id)]
    assert "checkpoints" in artifacts


@pytest.mark.skipif(not MLFLOW_AVAILABLE, reason="mlflow is not installed")
def test_tracker_artifact_location_separate_from_db(tmp_path):
    """Proves that tracker configures a dedicated artifact directory separate from SQLite db."""
    db_file = tmp_path / "metadata" / "mlflow.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    tracking_uri = f"sqlite:///{db_file}"
    artifact_root = tmp_path / "custom_artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    exp_name = "test_separate_artifact_exp"

    tracker = MLflowTracker(
        enabled=True,
        tracking_uri=tracking_uri,
        artifact_location=str(artifact_root),
        experiment_name=exp_name,
        run_name="separate_artifact_run",
    )

    with tracker:
        tracker.log_dict_artifact({"test": "data"}, "reports/summary.json")

    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(exp_name)
    assert experiment.artifact_location == str(artifact_root)
    # Check that artifact file actually landed under custom_artifacts
    summary_files = list(artifact_root.glob("**/summary.json"))
    assert len(summary_files) == 1


@pytest.mark.skipif(not MLFLOW_AVAILABLE, reason="mlflow is not installed")
def test_end_to_end_synthetic_run_records_metrics_and_artifacts(synthetic_dataset_dir, tmp_path):
    """
    Verifies that a complete small training and evaluation pipeline with MLflow:
    1. Records actual train/val loss and accuracy metrics per epoch.
    2. Records evaluation metrics across conditions (original, heavy_hematoxylin, reconstruction_only).
    3. Saves retrievable JSON artifacts in MLflow.
    """
    db_file = tmp_path / "metadata" / "mlflow.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    tracking_uri = f"sqlite:///{db_file}"
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    exp_name = "test_end_to_end_synthetic"

    from src.train import run_training
    from src.evaluate import run_stress_test

    tracker = MLflowTracker(
        enabled=True,
        tracking_uri=tracking_uri,
        artifact_location=str(artifact_root),
        experiment_name=exp_name,
        run_name="end_to_end_synthetic_run",
        run_type="smoke_test",
    )

    models_dir = tmp_path / "models"
    eval_json = tmp_path / "eval_results.json"

    with tracker:
        ckpt_path = run_training(
            data_dir=synthetic_dataset_dir,
            output_dir=models_dir,
            model_name="small_e2e_model",
            train_mode="train_standard",
            pretrained=False,
            epochs=1,
            batch_size=8,
            max_samples_per_class=3,
            device="cpu",
            seed=42,
            tracker=tracker,
        )

        run_stress_test(
            checkpoint_path=ckpt_path,
            data_dir=synthetic_dataset_dir,
            batch_size=8,
            device="cpu",
            output_json=eval_json,
            tracker=tracker,
        )

    # Now verify via MLflowClient
    client = mlflow.tracking.MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(exp_name)
    assert experiment is not None
    runs = client.search_runs(experiment_ids=[experiment.experiment_id])
    assert len(runs) == 1
    run = runs[0]

    # Verify actual training & validation metrics exist and are non-empty floats
    assert "train/loss" in run.data.metrics
    assert "train/accuracy" in run.data.metrics
    assert "val/loss" in run.data.metrics
    assert "val/accuracy" in run.data.metrics
    assert 0.0 <= run.data.metrics["train/accuracy"] <= 1.0

    # Verify evaluation metrics across conditions
    assert "eval_original/accuracy" in run.data.metrics
    assert "eval_reconstruction_only/accuracy" in run.data.metrics
    assert "eval_heavy_hematoxylin/accuracy" in run.data.metrics

    # Verify JSON artifacts are saved and retrievable
    artifact_paths = [a.path for a in client.list_artifacts(run.info.run_id)]
    assert "eval_results.json" in artifact_paths

    downloaded_summary_path = client.download_artifacts(run.info.run_id, "eval_results.json")
    with open(downloaded_summary_path, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
    assert "profiles" in loaded_data
    assert "original" in loaded_data["profiles"]
    assert "heavy_hematoxylin" in loaded_data["profiles"]


