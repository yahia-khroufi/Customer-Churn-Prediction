import pandas as pd


ID_COLUMN = "customerID"
TARGET_COLUMN = "Churn"
TARGET_VALUES = ["No", "Yes"]

NUMERIC_FEATURES = [
    "tenure",
    "MonthlyCharges",
    "TotalCharges",
]

CATEGORY_VALUES = {
    "gender": ["Male", "Female"],
    "SeniorCitizen": [0, 1],
    "Partner": ["Yes", "No"],
    "Dependents": ["Yes", "No"],
    "PhoneService": ["Yes", "No"],
    "MultipleLines": ["Yes", "No", "No phone service"],
    "InternetService": ["DSL", "Fiber optic", "No"],
    "OnlineSecurity": ["Yes", "No", "No internet service"],
    "OnlineBackup": ["Yes", "No", "No internet service"],
    "DeviceProtection": ["Yes", "No", "No internet service"],
    "TechSupport": ["Yes", "No", "No internet service"],
    "StreamingTV": ["Yes", "No", "No internet service"],
    "StreamingMovies": ["Yes", "No", "No internet service"],
    "Contract": ["Month-to-month", "One year", "Two year"],
    "PaperlessBilling": ["Yes", "No"],
    "PaymentMethod": [
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ],
}

CATEGORICAL_FEATURES = list(CATEGORY_VALUES.keys())
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def validate_data(df: pd.DataFrame, training: bool = True) -> dict:
    errors = []
    warnings = []

    if df.empty:
        errors.append("Le dataset est vide.")
        return {"errors": errors, "warnings": warnings}

    required_columns = FEATURE_COLUMNS.copy()

    if training:
        required_columns.append(TARGET_COLUMN)

    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        errors.append(
            f"Colonnes manquantes : {sorted(missing_columns)}"
        )
        return {"errors": errors, "warnings": warnings}

    for column in FEATURE_COLUMNS:
        missing_count = df[column].isna().sum()

        if missing_count > 0:
            warnings.append(
                f"{column} : {missing_count} valeur(s) manquante(s)."
            )

    for column, allowed_values in CATEGORY_VALUES.items():

        invalid = (
            df[column].notna()
            & ~df[column].isin(allowed_values)
        )

        if invalid.any():
            errors.append(
                f"{column} contient des valeurs non autorisées."
            )

    for column in NUMERIC_FEATURES:

        converted = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        invalid = (
            df[column].notna()
            & converted.isna()
        )

        if invalid.any():
            errors.append(
                f"{column} contient des valeurs non numériques."
            )

    # 6. Vérifier la cible
    if training:

        invalid_target = (
            df[TARGET_COLUMN].notna()
            & ~df[TARGET_COLUMN].isin(TARGET_VALUES)
        )

        if invalid_target.any():
            errors.append(
                "Churn accepte seulement 'Yes' ou 'No'."
            )

    return {
        "errors": errors,
        "warnings": warnings,
    }