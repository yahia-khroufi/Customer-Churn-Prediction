import argparse
import json
import hashlib
from pathlib import Path

import pandas as pd
import mlflow.sklearn as ml
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from src.common.data_contract import FEATURE_COLUMNS
from src.data.preprocess import prepare_prediction_data
from src.models.persistence import DEFAULT_MODEL_PATH


class ChurnPredictor:
    def __init__(self, model_path: str | Path = DEFAULT_MODEL_PATH):
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Pipeline absent : {self.model_path}. Exécuter python run_pipeline.py --evaluate."
            )
        self.model = ml.load_model(self.model_path)
        if not isinstance(self.model, Pipeline):
            raise ValueError("Le fichier doit contenir un Pipeline scikit-learn.")
        check_is_fitted(self.model)
        if list(self.model.feature_names_in_) != FEATURE_COLUMNS:
            raise ValueError("Les colonnes du modèle ne correspondent pas au contrat courant.")
        if set(self.model.classes_) != {0, 1}:
            raise ValueError("Le modèle doit prédire les classes 0 et 1.")
        self.model_name = type(self.model.named_steps["classifier"]).__name__
        self.metadata = {}
        metadata_path = self.model_path.with_suffix(".json")
        if metadata_path.is_file():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                digest = hashlib.sha256(self.model_path.read_bytes()).hexdigest()
                if metadata.get("model_sha256") == digest:
                    self.metadata = metadata
            except (ValueError, OSError, AttributeError):
                pass

    def predict(self, customer: dict) -> dict:
        X = prepare_prediction_data(pd.DataFrame([customer]))
        prediction = int(self.model.predict(X)[0])
        positive_index = list(self.model.classes_).index(1)
        probability = float(self.model.predict_proba(X)[0, positive_index])
        return {
            "prediction": "Yes" if prediction == 1 else "No",
            "churn_probability": probability,
            "threshold": 0.5,
            "model_name": self.model_name,
        }


def main():
    parser = argparse.ArgumentParser(description="Prédire le churn d'un client décrit en JSON.")
    parser.add_argument("input", type=Path, help="Fichier JSON contenant les 19 caractéristiques.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    args = parser.parse_args()
    customer = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(customer, dict):
        parser.error("Le fichier JSON doit contenir un objet client.")
    print(json.dumps(ChurnPredictor(args.model).predict(customer), indent=2))


if __name__ == "__main__":
    main()
