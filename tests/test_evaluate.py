"""Métriques connues à l'avance et protection du modèle pendant l'évaluation."""

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import NotFittedError
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.models.evaluate import evaluate_model


@pytest.fixture
def evaluation_data():
    X = pd.DataFrame({"tenure": [1.0, 10.0, 20.0, 30.0]})
    y = pd.Series([0, 0, 1, 1], name="Churn")
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", DummyClassifier(strategy="constant", constant=0)),
    ])
    model.fit(X, y)
    return model, X, y


def test_no_predicted_churn_returns_zero_precision_recall_and_f1(evaluation_data):
    model, X, y = evaluation_data

    result = evaluate_model(model, X, y)

    assert result["metrics"] == pytest.approx({
        "accuracy": 0.5, "precision": 0.0, "recall": 0.0,
        "f1_score": 0.0, "roc_auc": 0.5,
    })
    assert result["confusion_matrix"] == [[2, 0], [2, 0]]


def test_auc_uses_positive_class_probabilities(evaluation_data, monkeypatch):
    model, X, y = evaluation_data
    # Ordre inversé : la probabilité de Churn=1 est dans la première colonne.
    model.named_steps["classifier"].classes_ = np.array([1, 0])
    monkeypatch.setattr(model, "predict", lambda data: np.array([0, 1, 0, 1]))
    monkeypatch.setattr(model, "predict_proba", lambda data: np.array([
        [0.1, 0.9], [0.6, 0.4], [0.4, 0.6], [0.8, 0.2],
    ]))

    result = evaluate_model(model, X, y)

    assert result["metrics"] == pytest.approx({
        "accuracy": 0.5, "precision": 0.5, "recall": 0.5,
        "f1_score": 0.5, "roc_auc": 0.75,
    })
    assert result["confusion_matrix"] == [[1, 1], [1, 1]]


def test_evaluation_does_not_refit_or_modify_inputs(evaluation_data, monkeypatch):
    model, X, y = evaluation_data
    original_X, original_y = X.copy(deep=True), y.copy(deep=True)
    scaler = model.named_steps["scaler"]
    original_mean = scaler.mean_.copy()

    def forbidden_fit(*args, **kwargs):
        pytest.fail("L'évaluation ne doit jamais entraîner le modèle.")

    monkeypatch.setattr(model, "fit", forbidden_fit)
    monkeypatch.setattr(scaler, "fit", forbidden_fit)
    monkeypatch.setattr(model.named_steps["classifier"], "fit", forbidden_fit)

    evaluate_model(model, X, y)

    pd.testing.assert_frame_equal(X, original_X)
    pd.testing.assert_series_equal(y, original_y)
    np.testing.assert_array_equal(scaler.mean_, original_mean)


def test_single_class_test_set_has_no_auc(evaluation_data):
    model, X, y = evaluation_data

    with pytest.warns(UserWarning, match="une seule classe"):
        result = evaluate_model(model, X.iloc[:2], y.iloc[:2])

    assert result["metrics"]["roc_auc"] is None
    assert result["confusion_matrix"] == [[2, 0], [0, 0]]


def test_unfitted_model_is_rejected(evaluation_data):
    _, X, y = evaluation_data
    model = Pipeline([("classifier", DummyClassifier())])

    with pytest.raises(NotFittedError):
        evaluate_model(model, X, y)


@pytest.mark.parametrize("invalid_case", ["empty", "length", "index", "label", "missing"])
def test_invalid_test_data_is_rejected(evaluation_data, invalid_case):
    model, X, y = evaluation_data
    if invalid_case == "empty":
        X, y = X.iloc[:0], y.iloc[:0]
    elif invalid_case == "length":
        y = y.iloc[:2]
    elif invalid_case == "index":
        y = y.iloc[::-1]
    elif invalid_case == "label":
        y.iloc[0] = 2
    else:
        y = y.astype(float)
        y.iloc[0] = np.nan

    with pytest.raises(ValueError):
        evaluate_model(model, X, y)
