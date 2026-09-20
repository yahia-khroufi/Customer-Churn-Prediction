"""Petit entraînement réel sur un CSV temporaire, jamais sur le dataset brut."""

import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone

from src.data.preprocess import prepare_training_data
from src.models.train import train_model


@pytest.fixture(autouse=True)
def small_parameter_grids(monkeypatch):
    """Une petite grille suffit pour vérifier le fonctionnement de la recherche."""
    monkeypatch.setattr("src.models.train.PARAM_GRIDS", {
        "LogisticRegression": {"classifier__C": [0.1, 1.0]},
        "DecisionTreeClassifier": {"classifier__max_depth": [3, 5]},
        "RandomForestClassifier": {"classifier__n_estimators": [5, 10]},
        "XGBClassifier": {"classifier__n_estimators": [5, 10]},
    })


def test_training_returns_fitted_pipeline_and_reserved_test_set(valid_data, tmp_path):
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

    X, _ = prepare_training_data(data)
    X_train = X.drop(index=X_test.index)
    numeric_pipeline = model.named_steps["preprocessor"].named_transformers_["numeric"]
    imputer = numeric_pipeline.named_steps["imputer"]
    np.testing.assert_allclose(
        imputer.statistics_, X_train[["tenure", "MonthlyCharges", "TotalCharges"]].median(),
    )
    if "scaler" in numeric_pipeline.named_steps:
        scaler = numeric_pipeline.named_steps["scaler"]
        assert scaler.n_samples_seen_ == len(X_train)
    assert csv_path.read_bytes() == original_csv


def test_selection_uses_f1_without_rounding_and_cv_excludes_test(valid_data, tmp_path, monkeypatch):
    data = pd.concat([valid_data] * 10, ignore_index=True)
    csv_path = tmp_path / "selection.csv"
    data.to_csv(csv_path, index=False)
    seen_indices = []
    seen_splits = []
    seen_models = []
    searched_models = []
    search_indices = []
    search_splits = []
    # Deux scores s'affichent tous deux 0.7000, mais le dernier est meilleur.
    f1_scores = [0.5, 0.6, 0.70001, 0.70002]

    def controlled_cv(candidate, X, y, cv, scoring, error_score):
        name = type(candidate.named_steps["classifier"]).__name__
        seen_models.append(name)
        seen_indices.append(set(X.index))
        seen_splits.append([(a.tolist(), b.tolist()) for a, b in cv.split(X, y)])
        numeric = candidate.named_steps["preprocessor"].transformers[0][1]
        assert ("scaler" in numeric.named_steps) == (name == "LogisticRegression")
        # L'accuracy favorise le premier modèle, le F1 favorise XGBoost.
        return {
            "test_accuracy": np.full(5, 0.99 if len(seen_models) == 1 else 0.8),
            "test_precision": np.full(5, 0.7),
            "test_recall": np.full(5, 0.7),
            "test_f1": np.full(5, f1_scores[len(seen_models) - 1]),
        }

    monkeypatch.setattr("src.models.train.cross_validate", controlled_cv)

    class ControlledSearch:
        def __init__(self, estimator, param_grid, scoring, refit, cv, n_jobs, error_score):
            assert refit == "f1"
            self.estimator = estimator
            self.cv = cv

        def fit(self, X, y):
            name = type(self.estimator.named_steps["classifier"]).__name__
            searched_models.append(name)
            search_indices.append(set(X.index))
            search_splits.append([(a.tolist(), b.tolist()) for a, b in self.cv.split(X, y)])
            # Le réglage inverse le classement initial, même après arrondi à 4 décimales.
            f1 = 0.80002 if name == "RandomForestClassifier" else 0.80001
            self.best_index_ = 0
            self.best_params_ = {"classifier__n_estimators": 10}
            self.cv_results_ = {
                "mean_test_accuracy": [0.8],
                "mean_test_precision": [0.7],
                "mean_test_recall": [0.7],
                "mean_test_f1": [f1],
                "std_test_f1": [0.01],
            }
            self.best_estimator_ = clone(self.estimator).set_params(**self.best_params_)
            self.best_estimator_.fit(X, y)
            return self

    monkeypatch.setattr("src.models.train.GridSearchCV", ControlledSearch)
    model, X_test, _ = train_model(csv_path)

    assert seen_models == [
        "LogisticRegression", "DecisionTreeClassifier",
        "RandomForestClassifier", "XGBClassifier",
    ]
    assert searched_models == ["XGBClassifier", "RandomForestClassifier"]
    assert type(model.named_steps["classifier"]).__name__ == "RandomForestClassifier"
    assert model.named_steps["classifier"].n_estimators == 10
    assert all(indices == set(data.index) - set(X_test.index) for indices in seen_indices)
    assert all(splits == seen_splits[0] for splits in seen_splits)
    assert all(indices == seen_indices[0] for indices in search_indices)
    assert all(splits == seen_splits[0] for splits in search_splits)
    assert len(model.predict(X_test)) == len(X_test)


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
