from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.metadata
import json

import joblib
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from src.utils.logger import get_logger


logger = get_logger(__name__)

EXPERIMENT_NAME = "customer-churn"
MODEL_NAME = "churn-pipeline"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "churn_pipeline.joblib"


def register_pipeline(
    model: Pipeline,
    input_example: pd.DataFrame,
) -> str:
    import mlflow
    import mlflow.sklearn
    from mlflow.models import infer_signature

    check_is_fitted(model)

    if mlflow.active_run() is None:
        mlflow.set_experiment(EXPERIMENT_NAME)
    context = mlflow.start_run() if mlflow.active_run() is None else nullcontext(mlflow.active_run())
    with context as run:

        model_info = mlflow.sklearn.log_model(
            sk_model=model,
            name="pipeline",
            input_example=input_example.head(5),
            registered_model_name=MODEL_NAME,
            serialization_format="cloudpickle",
            signature=infer_signature(input_example, model.predict(input_example)),
            pip_requirements=[
                f"{package}=={importlib.metadata.version(package)}"
                for package in ["scikit-learn", "pandas", "numpy", "joblib", "xgboost"]
            ],
        )

        logger.info(
            "Pipeline enregistré dans MLflow - run_id=%s",
            run.info.run_id,
        )

        return model_info.model_uri


def save_pipeline(model: Pipeline, path: str | Path = DEFAULT_MODEL_PATH) -> Path:
    check_is_fitted(model)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path, compress=3)
    logger.info("Pipeline sauvegardé : %s", path.resolve())
    return path


def save_model_metadata(model: Pipeline, path: str | Path, evaluation: dict, test_samples: int) -> Path:
    path = Path(path)
    metadata = {
        "model_name": type(model.named_steps["classifier"]).__name__,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "features": list(model.feature_names_in_),
        "test_samples": test_samples,
        "evaluation": evaluation,
        "training": getattr(model, "training_summary_", {}),
        "versions": {
            package: importlib.metadata.version(package)
            for package in ["scikit-learn", "pandas", "numpy", "joblib", "xgboost"]
        },
    }
    metadata_path = path.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    logger.info("Rapport du modèle : %s", metadata_path)
    return metadata_path
