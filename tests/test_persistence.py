"""Le pipeline rechargé doit conserver ses transformations et prédictions."""

import joblib
import numpy as np
import pytest
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.data.preprocess import (
    build_preprocessor,
    prepare_prediction_data,
    prepare_training_data,
)
from src.models.persistence import save_pipeline


def test_saved_pipeline_preserves_predictions(valid_data, tmp_path):
    X, y = prepare_training_data(valid_data)
    model = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", LogisticRegression(max_iter=1000)),
    ])
    model.fit(X, y)
    customers = valid_data.drop(columns="Churn").copy()
    customers.loc[0, "TotalCharges"] = " "
    customers.loc[1, "Contract"] = "Two year"
    with pytest.warns(UserWarning, match="TotalCharges"):
        new_X = prepare_prediction_data(customers)
    expected_classes = model.predict(new_X)
    expected_probabilities = model.predict_proba(new_X)

    path = save_pipeline(model, tmp_path / "models" / "pipeline.joblib")
    loaded = joblib.load(path)

    assert path.is_file()
    np.testing.assert_array_equal(loaded.predict(new_X), expected_classes)
    np.testing.assert_allclose(loaded.predict_proba(new_X), expected_probabilities)
    np.testing.assert_allclose(
        loaded.named_steps["preprocessor"].transform(new_X),
        model.named_steps["preprocessor"].transform(new_X),
    )


def test_unfitted_pipeline_is_not_saved(tmp_path):
    model = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", LogisticRegression()),
    ])
    path = tmp_path / "pipeline.joblib"

    with pytest.raises(NotFittedError):
        save_pipeline(model, path)

    assert not path.exists()
