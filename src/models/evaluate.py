"""Évaluation d'un modèle déjà entraîné sur le jeu de test réservé.

Ce fichier ne fait aucun fit. L'appel depuis train.py passe le Pipeline entraîné,
X_test et y_test à evaluate_model.
"""

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


def evaluate_model(model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    """Affiche et retourne les métriques et la matrice de confusion.

    La classe positive est 1 : le client quitte l'entreprise (Churn = Yes).
    X_test doit déjà être préparé, comme dans train_model. Le Pipeline applique
    son preprocessing appris sur le train, sans le réajuster sur le test.
    """
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

    # 1. Classes prédites : pour accuracy, precision, recall, F1 et la matrice.
    y_pred = model.predict(X_test)

    # 2. Probabilité de la classe 1 : pour la ROC-AUC, jamais les classes prédites.
    positive_class_index = classes.index(1)
    y_probability = model.predict_proba(X_test)[:, positive_class_index]

    # zero_division=0 donne un score nul si un ratio est impossible à calculer,
    # par exemple la précision quand le modèle ne prédit aucun départ.
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "f1_score": float(f1_score(y_test, y_pred, pos_label=1, zero_division=0)),
    }

    # La ROC-AUC nécessite au moins un exemple de chaque classe dans le test.
    if y_test.nunique() == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_test, y_probability))
    else:
        metrics["roc_auc"] = None
        warnings.warn(
            "ROC-AUC non définie : une seule classe est présente dans y_test.",
            UserWarning,
            stacklevel=2,
        )

    # Lignes = classes réelles, colonnes = classes prédites, dans l'ordre No, Yes.
    matrix = confusion_matrix(y_test, y_pred, labels=[0, 1])
    matrix_table = pd.DataFrame(
        matrix,
        index=["Réel No (0)", "Réel Yes (1)"],
        columns=["Prédit No (0)", "Prédit Yes (1)"],
    )

    print(f"\nÉvaluation finale sur {len(y_test)} clients du test :")
    for name, value in metrics.items():
        if value is None:
            print(f"{name}: non définie")
        else:
            print(f"{name}: {value:.4f}")
    print("\nMatrice de confusion :")
    print(matrix_table.to_string())
    print("\nLe modèle et le preprocessing n'ont pas été réentraînés sur le test.")

    return {
        "metrics": metrics,
        "confusion_matrix": matrix.tolist(),
    }
