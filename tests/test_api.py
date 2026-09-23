import json

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from api.main import create_app
from src.data.preprocess import build_preprocessor, prepare_training_data
from src.models.persistence import save_model_metadata, save_pipeline
from src.models.predict import ChurnPredictor

@pytest.fixture
def api_data(valid_data, tmp_path):
    X, y = prepare_training_data(valid_data)
    model = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", LogisticRegression(max_iter=1000)),
    ]).fit(X, y)
    path = save_pipeline(model, tmp_path / "model.joblib")
    customer = valid_data.drop(columns=["Churn", "customerID"]).iloc[0].to_dict()
    customer["TotalCharges"] = float(customer["TotalCharges"])
    return path, customer, model


def test_api_prediction_matches_saved_pipeline(api_data):
    path, customer, model = api_data
    expected = ChurnPredictor(path).predict(customer)
    with TestClient(create_app(path)) as client:
        assert client.get("/health").json() == {"status": "ok", "model_loaded": True}
        result = client.post("/predict", json=customer)
        assert result.status_code == 200
        assert result.json() == expected
        assert 0 <= result.json()["churn_probability"] <= 1
        assert client.get("/").status_code == 200
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/static/styles.css").status_code == 200
        assert len(client.get("/schema").json()["features"]) == 19


@pytest.mark.parametrize("field,value", [
    ("gender", "Unknown"), ("Contract", "bad"), ("SeniorCitizen", 2),
    ("SeniorCitizen", True), ("tenure", -1), ("tenure", 1.5),
    ("MonthlyCharges", -1), ("TotalCharges", "NaN"),
    ("TotalCharges", "Infinity"), ("Churn", "Yes"),
    ("PhoneService", "No"), ("InternetService", "No"),
])
def test_invalid_customer_returns_422(api_data, field, value):
    path, customer, _ = api_data
    customer[field] = value
    with TestClient(create_app(path)) as client:
        assert client.post("/predict", json=customer).status_code == 422


def test_missing_required_field_is_rejected(api_data):
    path, customer, _ = api_data
    del customer["Contract"]
    with TestClient(create_app(path)) as client:
        assert client.post("/predict", json=customer).status_code == 422


def test_missing_total_charges_uses_imputer(api_data):
    path, customer, _ = api_data
    customer["TotalCharges"] = None
    with TestClient(create_app(path)) as client, pytest.warns(UserWarning, match="TotalCharges"):
        response = client.post("/predict", json=customer)
    assert response.status_code == 200
    assert np.isfinite(response.json()["churn_probability"])


def test_missing_model_returns_503_without_leaking_path(api_data, tmp_path):
    _, customer, _ = api_data
    with TestClient(create_app(tmp_path / "missing.joblib")) as client:
        assert client.get("/health").status_code == 503
        response = client.post("/predict", json=customer)
        assert response.status_code == 503
        assert str(tmp_path) not in response.text
        assert client.get("/model-info").status_code == 503
        assert client.get("/").status_code == 200


def test_model_metadata_matches_artifact(api_data):
    path, _, model = api_data
    evaluation = {"metrics": {"recall": 0.5, "f1_score": 0.4}}
    metadata_path = save_model_metadata(model, path, evaluation, 4)
    with TestClient(create_app(path)) as client:
        info = client.get("/model-info").json()
        assert info["evaluation"] == evaluation
        assert info["test_samples"] == 4
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["model_sha256"] = "outdated"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with TestClient(create_app(path)) as client:
        assert client.get("/model-info").json()["evaluation"] is None


def test_predictor_requires_model_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="Pipeline absent"):
        ChurnPredictor(tmp_path / "missing.joblib")

