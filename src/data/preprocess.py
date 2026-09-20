import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.common.data_contract import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    validate_data,
)


def clean_data(df: pd.DataFrame, training: bool = True) -> pd.DataFrame:

    if not df.columns.is_unique:
        raise ValueError("Plusieurs colonnes portent le même nom.")

    cleaned = df.replace(r"^\s*$", pd.NA, regex=True)
    text_columns = cleaned.select_dtypes(include=["object", "string"]).columns
    for column in text_columns:
        if pd.api.types.is_string_dtype(cleaned[column].dropna()):
            cleaned[column] = cleaned[column].astype("string").str.strip()
            cleaned[column] = cleaned[column].replace("", pd.NA)

    if "OnlineBackup" in cleaned.columns:
        invalid_backup = cleaned["OnlineBackup"].eq("ajmnxx").fillna(False)
        if invalid_backup.any():
            warnings.warn(
                f"OnlineBackup : {int(invalid_backup.sum())} valeur(s) 'ajmnxx' "
                "remplacée(s) par une valeur manquante, sans deviner la catégorie.",
                UserWarning,
                stacklevel=2,
            )
            cleaned.loc[invalid_backup, "OnlineBackup"] = pd.NA

    report = validate_data(cleaned, training=training)


    if training and TARGET_COLUMN in cleaned.columns:
        missing_target = int(cleaned[TARGET_COLUMN].isna().sum())
        if missing_target:
            report["errors"].append(
                f"{TARGET_COLUMN} : {missing_target} cible(s) manquante(s). "
                "Leur traitement doit être décidé avant l'entraînement."
            )
    elif not training and TARGET_COLUMN in cleaned.columns:
        report["errors"].append(
            f"{TARGET_COLUMN} ne doit pas être fourni pour une prédiction."
        )

    if report["errors"]:
        raise ValueError("Contrat de données non respecté :\n- " + "\n- ".join(report["errors"]))
    for message in report["warnings"]:
        warnings.warn(message, UserWarning, stacklevel=2)

    for column in NUMERIC_FEATURES + ["SeniorCitizen"]:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="raise").astype("float64")

    for column in CATEGORICAL_FEATURES:
        if column != "SeniorCitizen":
            values = cleaned[column].astype(object)
            cleaned[column] = values.where(values.notna(), np.nan)

    return cleaned


def prepare_training_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:

    cleaned = clean_data(df, training=True)
    X = cleaned[FEATURE_COLUMNS].copy()
    y = cleaned[TARGET_COLUMN].map({"No": 0, "Yes": 1}).astype("int64")
    return X, y


def prepare_prediction_data(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = clean_data(df, training=False)
    return cleaned[FEATURE_COLUMNS].copy()


def build_preprocessor(scale_numeric: bool = True) -> ColumnTransformer:

    numeric_steps = [
        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
    ]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    numeric_pipeline = Pipeline(numeric_steps)
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(
            strategy="constant", fill_value="Missing", keep_empty_features=True,
        )),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    text_features = CATEGORICAL_FEATURES.copy()
    text_features.remove("SeniorCitizen")

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("binary", SimpleImputer(strategy="most_frequent", keep_empty_features=True), ["SeniorCitizen"]),
            ("categorical", categorical_pipeline, text_features),
        ],
        remainder="drop",
    )

    