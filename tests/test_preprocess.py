"""Nettoyage, séparation de la cible et transformations apprises sur le train."""

import numpy as np
import pandas as pd
import pytest

from src.common.data_contract import FEATURE_COLUMNS
from src.data.preprocess import (
    build_preprocessor,
    clean_data,
    prepare_prediction_data,
    prepare_training_data,
)


def test_training_data_excludes_target_and_identifier(valid_data):
    original = valid_data.copy(deep=True)

    X, y = prepare_training_data(valid_data)

    assert list(X.columns) == FEATURE_COLUMNS
    assert "Churn" not in X.columns
    assert "customerID" not in X.columns
    assert y.tolist() == [0, 1, 0, 1]
    assert X.index.equals(y.index)
    pd.testing.assert_frame_equal(valid_data, original)


def test_cleaning_keeps_missing_values_until_preprocessing(valid_data):
    valid_data.loc[0, "TotalCharges"] = "   "
    valid_data.loc[1, "Partner"] = " Yes "
    original = valid_data.copy(deep=True)

    with pytest.warns(UserWarning, match="TotalCharges"):
        cleaned = clean_data(valid_data)

    assert pd.isna(cleaned.loc[0, "TotalCharges"])
    assert cleaned.loc[1, "Partner"] == "Yes"
    assert cleaned.loc[1, "TotalCharges"] == 600.0
    pd.testing.assert_frame_equal(valid_data, original)


def test_known_backup_typo_becomes_missing_with_warning(valid_data):
    valid_data.loc[0, "OnlineBackup"] = "ajmnxx"

    with pytest.warns(UserWarning, match="OnlineBackup"):
        cleaned = clean_data(valid_data)

    assert pd.isna(cleaned.loc[0, "OnlineBackup"])


def test_missing_target_is_rejected(valid_data):
    valid_data.loc[0, "Churn"] = None

    with pytest.raises(ValueError, match="Churn"):
        prepare_training_data(valid_data)


def test_duplicate_column_names_are_rejected(valid_data):
    duplicated = pd.concat([valid_data, valid_data[["tenure"]]], axis=1)

    with pytest.raises(ValueError, match="même nom"):
        clean_data(duplicated)


def test_prediction_rejects_target(valid_data):
    with pytest.raises(ValueError, match="Churn"):
        prepare_prediction_data(valid_data)


def test_prediction_returns_features_in_expected_order(valid_data):
    customers = valid_data.drop(columns=["Churn", "customerID"])
    customers = customers[customers.columns[::-1]]

    X = prepare_prediction_data(customers)

    assert list(X.columns) == FEATURE_COLUMNS


@pytest.mark.parametrize("scale_numeric", [True, False])
def test_numeric_scaling_can_be_enabled_or_disabled(valid_data, scale_numeric):
    X, _ = prepare_training_data(valid_data)
    preprocessor = build_preprocessor(scale_numeric=scale_numeric)

    transformed = preprocessor.fit_transform(X)

    assert np.isfinite(transformed).all()
    numeric = transformed[:, :3]
    if scale_numeric:
        np.testing.assert_allclose(numeric.mean(axis=0), 0, atol=1e-10)
        np.testing.assert_allclose(numeric.std(axis=0), 1)
    else:
        np.testing.assert_allclose(numeric, X[["tenure", "MonthlyCharges", "TotalCharges"]])


def test_imputation_uses_train_statistics_only(valid_data):
    X, _ = prepare_training_data(valid_data)
    train = X.iloc[:3].copy()
    test = X.iloc[[3]].copy()
    test.loc[:, "tenure"] = np.nan
    test.loc[:, "TotalCharges"] = 1_000_000.0
    preprocessor = build_preprocessor(scale_numeric=False)
    preprocessor.fit(train)
    imputer = preprocessor.named_transformers_["numeric"].named_steps["imputer"]
    learned_medians = imputer.statistics_.copy()

    transformed = preprocessor.transform(test)

    # La médiane des trois tenures du train (1, 12, 24) est 12.
    assert transformed[0, 0] == 12.0
    np.testing.assert_array_equal(imputer.statistics_, learned_medians)


def test_missing_categories_and_unseen_valid_category_can_be_transformed(valid_data):
    X, _ = prepare_training_data(valid_data)
    preprocessor = build_preprocessor()
    preprocessor.fit(X)
    customers = valid_data.iloc[[0]].drop(columns="Churn").copy()
    customers.loc[:, "Contract"] = "Two year"  # Valide, absent du train.
    customers.loc[:, "Partner"] = None
    customers["SeniorCitizen"] = np.nan

    with pytest.warns(UserWarning):
        test = prepare_prediction_data(customers)
    transformed = preprocessor.transform(test)

    assert np.isfinite(transformed).all()
    assert transformed.shape[1] == preprocessor.transform(X).shape[1]
    assert transformed[0, 3] == 0.0
