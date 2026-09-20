"""Le contrat accepte les données valides et signale les erreurs de saisie."""

import numpy as np
import pytest

from src.common.data_contract import CATEGORY_VALUES, validate_data


def test_valid_data_is_accepted(valid_data):
    report = validate_data(valid_data)

    assert report == {"errors": [], "warnings": []}


def test_empty_dataset_is_rejected(valid_data):
    report = validate_data(valid_data.iloc[:0])

    assert report["errors"]


@pytest.mark.parametrize("column", ["tenure", "Contract", "Churn"])
def test_missing_required_column_is_rejected(valid_data, column):
    report = validate_data(valid_data.drop(columns=column))

    assert any(column in message for message in report["errors"])


@pytest.mark.parametrize("column", list(CATEGORY_VALUES))
def test_invalid_category_is_rejected(valid_data, column):

    valid_data[column] = valid_data[column].astype(object)
    valid_data.loc[0, column] = "INVALID"

    report = validate_data(valid_data)

    assert any(column in message for message in report["errors"])


def test_invalid_numeric_value_is_rejected(valid_data):
    valid_data.loc[0, "TotalCharges"] = "not-a-number"

    report = validate_data(valid_data)

    assert any("TotalCharges" in message for message in report["errors"])


def test_invalid_target_is_rejected(valid_data):
    valid_data.loc[0, "Churn"] = "Maybe"

    report = validate_data(valid_data)

    assert any("Churn" in message for message in report["errors"])


def test_missing_feature_is_a_warning(valid_data):
    valid_data.loc[0, "MonthlyCharges"] = np.nan

    report = validate_data(valid_data)

    assert report["errors"] == []
    assert any("MonthlyCharges" in message for message in report["warnings"])


def test_prediction_does_not_require_target_or_id(valid_data):
    customers = valid_data.drop(columns=["Churn", "customerID"])

    assert validate_data(customers, training=False)["errors"] == []
