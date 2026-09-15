import pandas as pd


ID_COLUMN = "customerID"
TARGET_COLUMN = "Churn"
TARGET_VALUES = ["No", "Yes"]

NUMERIC_FEATURES = ["tenure", "MonthlyCharges", "TotalCharges"]

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

CATEGORICAL_FEATURES = list(CATEGORY_VALUES)
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TRAINING_COLUMNS = [ID_COLUMN] + FEATURE_COLUMNS + [TARGET_COLUMN]


def validate_data(df: pd.DataFrame, training: bool = True) -> dict[str, list[str]]:
    
    report = {"errors": [], "warnings": []}
    errors = report["errors"]
    warnings = report["warnings"]

    if df.columns.duplicated().any():
        errors.append("Plusieurs colonnes portent le même nom.")
        return report

    required_columns = TRAINING_COLUMNS if training else FEATURE_COLUMNS
    missing_columns = sorted(set(required_columns) - set(df.columns))
    if missing_columns:
        errors.append(f"Colonnes obligatoires absentes : {missing_columns}.")

    if df.empty:
        errors.append("Le dataset ne contient aucune observation.")
    if errors:
        return report

    extra_columns = sorted(set(df.columns) - set(TRAINING_COLUMNS))
    if extra_columns:
        warnings.append(f"Colonnes non prévues, à exclure des features : {extra_columns}.")
    if not training and TARGET_COLUMN in df.columns:
        errors.append("Churn ne doit pas être fourni pour une prédiction.")

    checked = df.replace(r"^\s*$", pd.NA, regex=True)

    if ID_COLUMN in checked.columns:
        ids = checked[ID_COLUMN]
        if ids.isna().any():
            errors.append(f"{ID_COLUMN} : {int(ids.isna().sum())} identifiant(s) manquant(s).")
        if not ids.dropna().map(type).eq(str).all():
            errors.append(f"{ID_COLUMN} doit contenir des identifiants textuels.")
        duplicates = int(ids.dropna().duplicated().sum())
        if duplicates:
            errors.append(f"{ID_COLUMN} : {duplicates} identifiant(s) répété(s).")

    if training:
        target = checked[TARGET_COLUMN]
        if target.isna().any():
            errors.append(f"Churn : {int(target.isna().sum())} cible(s) manquante(s).")
        invalid_target = target.notna() & ~target.isin(TARGET_VALUES)
        if invalid_target.any():
            errors.append("Churn accepte uniquement 'No' et 'Yes'.")
        if target.dropna().nunique() < 2:
            warnings.append("La cible contient moins de deux classes dans ces données.")

    for column in FEATURE_COLUMNS:
        missing_count = int(checked[column].isna().sum())
        if missing_count:
            warnings.append(f"{column} : {missing_count} valeur(s) manquante(s), espaces vides inclus.")

    for column, allowed_values in CATEGORY_VALUES.items():
        values = checked[column]
        invalid = values.notna() & ~values.isin(allowed_values)
        if invalid.any():
            examples = values.loc[invalid].drop_duplicates().head(5).tolist()
            errors.append(f"{column} : {int(invalid.sum())} valeur(s) non autorisée(s), exemples : {examples}.")

    for column in NUMERIC_FEATURES:
        values = checked[column]
        numbers = pd.to_numeric(values, errors="coerce")
        invalid = values.notna() & numbers.isna()
        if invalid.any():
            errors.append(f"{column} : {int(invalid.sum())} valeur(s) non convertible(s) en nombre.")
        if values.dropna().map(type).eq(bool).any():
            errors.append(f"{column} doit contenir des nombres, pas des booléens.")
        if numbers.isin([float("inf"), float("-inf")]).any():
            errors.append(f"{column} contient une valeur infinie.")
        if numbers.lt(0).any():
            errors.append(f"{column} : {int(numbers.lt(0).sum())} valeur(s) négative(s).")
        if values.notna().any() and not pd.api.types.is_numeric_dtype(values.dtype):
            warnings.append(f"{column} : type {values.dtype}, conversion en numérique à prévoir.")
        if column == "tenure" and numbers.dropna().mod(1).ne(0).any():
            errors.append("tenure doit contenir un nombre entier de mois.")
        if column == "MonthlyCharges" and numbers.eq(0).any():
            warnings.append(f"MonthlyCharges : {int(numbers.eq(0).sum())} valeur(s) égale(s) à zéro, à vérifier sans correction automatique.")

    return report
