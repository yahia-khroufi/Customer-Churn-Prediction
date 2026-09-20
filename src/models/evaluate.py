

import warnings

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted
from src.utils.logger import get_logger

logger =get_logger(__name__)
def evaluate_model(model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict:

    check_is_fitted(model)
    if X_test.empty or len(X_test) != len(y_test):
        raise ValueError("X_test et y_test doivent être non vides et de même longueur.")
    if not X_test.index.equals(y_test.index):
        raise ValueError("Les index de X_test et y_test doivent être dans le même ordre.")
    if not y_test.isin([0, 1]).all():
        raise ValueError("y_test doit contenir uniquement 0 et 1, sans valeur manquante.")

    classes = list(model.classes_)
    if set(classes) != {0, 1}:
        raise ValueError("Le modèle doit avoir été entraîné avec les classes 0 et 1.")

    y_pred = model.predict(X_test)

    positive_class_index = classes.index(1)
    y_probability = model.predict_proba(X_test)[:, positive_class_index]

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "f1_score": float(f1_score(y_test, y_pred, pos_label=1, zero_division=0)),
    }

    if y_test.nunique() == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_test, y_probability))
    else:
        metrics["roc_auc"] = None
        warnings.warn(
            "ROC-AUC non définie : une seule classe est présente dans y_test.",
            UserWarning,
            stacklevel=2,
        )

    matrix = confusion_matrix(y_test, y_pred, labels=[0, 1])
    matrix_table = pd.DataFrame(
        matrix,
        index=["Réel No (0)", "Réel Yes (1)"],
        columns=["Prédit No (0)", "Prédit Yes (1)"],
    )

    logger.info(f"Évaluation finale sur {len(y_test)} clients du test :")
    for name, value in metrics.items():
        if value is None:
            logger.info(f"{name}: non définie")
        else:
            logger.info(f"{name}: {value:.4f}")
    logger.info("Matrice de confusion :")
    logger.info(matrix_table.to_string())

    return {
        "metrics": metrics,
        "confusion_matrix": matrix.tolist(),
    }
