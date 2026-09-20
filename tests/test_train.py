"""Petit entraînement réel sur un CSV temporaire, jamais sur le dataset brut."""

import numpy as np
import pandas as pd
import pytest

from src.data.preprocess import prepare_training_data
from src.models.train import train_model


def test_training_returns_fitted_pipeline_and_reserved_test_set(valid_data, tmp_path):
    # 40 clients suffisent pour les cinq plis, avec deux classes dans chaque pli.
    data = pd.concat([valid_data] * 10, ignore_index=True)
    data["customerID"] = [f"CLIENT-{i}" for i in range(len(data))]
    data["tenure"] = np.arange(1, len(data) + 1)
    csv_path = tmp_path / "customers.csv"
    data.to_csv(csv_path, index=False)
    original_csv = csv_path.read_bytes()

    model, X_test, y_test = train_model(csv_path)

    assert len(X_test) == 8
    assert X_test.index.equals(y_test.index)
    assert y_test.value_counts().to_dict() == {0: 4, 1: 4}
    probabilities = model.predict_proba(X_test)
    assert probabilities.shape == (8, 2)
    assert np.isfinite(probabilities).all()
    np.testing.assert_allclose(probabilities.sum(axis=1), 1)

    # Le scaler final doit avoir appris exclusivement sur les clients du train.
    X, _ = prepare_training_data(data)
    X_train = X.drop(index=X_test.index)
    numeric_pipeline = model.named_steps["preprocessor"].named_transformers_["numeric"]
    scaler = numeric_pipeline.named_steps["scaler"]
    np.testing.assert_allclose(
        scaler.mean_, X_train[["tenure", "MonthlyCharges", "TotalCharges"]].mean(),
    )
    assert scaler.n_samples_seen_ == len(X_train)
    assert csv_path.read_bytes() == original_csv


def test_training_rejects_single_class(valid_data, tmp_path):
    valid_data["Churn"] = "No"
    csv_path = tmp_path / "single_class.csv"
    valid_data.to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="deux classes"):
        train_model(csv_path)


def test_training_rejects_too_few_clients_for_cv(valid_data, tmp_path):
    data = pd.concat([valid_data] * 2, ignore_index=True)
    csv_path = tmp_path / "too_small.csv"
    data.to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="au moins 5"):
        train_model(csv_path)
