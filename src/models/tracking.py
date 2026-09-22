
import json
import os
from pathlib import Path

import pandas as pd

from src.data.preprocess import prepare_prediction_data
from src.models.persistence import register_pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def track_experiment(model, evaluation=None, model_path=None) -> str:
    import mlflow

    storage = PROJECT_ROOT / "mlruns"
    storage.mkdir(exist_ok=True)
    uri = os.environ.get("MLFLOW_TRACKING_URI", f"sqlite:///{(storage / 'mlflow.db').as_posix()}")
    mlflow.set_tracking_uri(uri)
    experiment_name = os.environ.get("MLFLOW_EXPERIMENT_NAME", "customer-churn")
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        options = {} if os.environ.get("MLFLOW_TRACKING_URI") else {"artifact_location": (storage / "artifacts").as_uri()}
        experiment_id = mlflow.create_experiment(experiment_name, **options)
    else:
        experiment_id = experiment.experiment_id
    summary = getattr(model, "training_summary_", {})
    classifier = model.named_steps["classifier"]
    example = json.loads((PROJECT_ROOT / "examples" / "customer.json").read_text(encoding="utf-8"))
    example_X = prepare_prediction_data(pd.DataFrame([example]))

    with mlflow.start_run(experiment_id=experiment_id, run_name=type(classifier).__name__) as run:
        mlflow.set_tags({"stage": "evaluated" if evaluation else "cv_only", "selection_metric": "f1"})
        mlflow.log_params({f"classifier__{key}": value for key, value in classifier.get_params().items()})
        for key in ["random_state", "cv_folds", "train_samples", "test_samples", "dataset_sha256"]:
            if key in summary:
                mlflow.log_param(key, summary[key])
        mlflow.log_dict(summary, "training_summary.json")
        for phase in ["baseline", "tuned"]:
            for row in summary.get(f"{phase}_results", []):
                with mlflow.start_run(experiment_id=experiment_id, run_name=f"{phase}-{row['modele']}", nested=True):
                    mlflow.log_params({"phase": phase, "model": row["modele"]})
                    mlflow.log_metrics({key: float(value) for key, value in row.items() if key != "modele"})
        if evaluation:
            mlflow.log_metrics({f"test_{key}": float(value) for key, value in evaluation["metrics"].items() if value is not None})
            mlflow.log_dict(evaluation, "evaluation.json")
        model_uri = register_pipeline(model, example_X)
        mlflow.set_tag("model_uri", model_uri)
        if model_path:
            mlflow.log_artifact(str(model_path), artifact_path="export")
            metadata = Path(model_path).with_suffix(".json")
            if metadata.exists():
                mlflow.log_artifact(str(metadata), artifact_path="export")
        return run.info.run_id
