"""Premier entraînement : référence majoritaire et régression logistique.

Depuis la racine du projet : python -m src.models.train
Le test est réservé à l'évaluation finale, déléguée à evaluate.py depuis le
point d'entrée du script. Aucun modèle n'est sauvegardé ici.
"""

from pathlib import Path

import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline

from src.common.data_contract import ID_COLUMN
from src.data.preprocess import build_preprocessor, prepare_training_data
from src.models.evaluate import evaluate_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "churn.csv"
RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_FOLDS = 5


def train_model(data_path: str | Path = DATA_PATH) -> tuple[Pipeline, pd.DataFrame, pd.Series]:

    df = pd.read_csv(data_path)

    X, y = prepare_training_data(df)
    if y.nunique() != 2:
        raise ValueError("L'entraînement nécessite les deux classes : No et Yes.")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )
    if y_train.value_counts().min() < CV_FOLDS:
        raise ValueError("Le train doit contenir au moins 5 clients de chaque classe.")

    print(f"Clients d'entraînement : {len(X_train)}")
    print(f"Clients réservés au test : {len(X_test)}")

    baseline = Pipeline([
        ("preprocessor", build_preprocessor(scale_numeric=True)),
        ("classifier", DummyClassifier(strategy="most_frequent")),
    ])

    model = Pipeline([
        ("preprocessor", build_preprocessor(scale_numeric=True)),
        ("classifier", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
    ])
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    results = []
    for name, candidate in [("Classe majoritaire", baseline), ("LogisticRegression", model)]:
        scores = cross_validate(
            candidate,
            X_train,
            y_train,
            cv=cv,
            scoring={"accuracy": "accuracy", "roc_auc": "roc_auc"},
            error_score="raise",
        )
        results.append({
            "modele": name,
            "accuracy_cv": scores["test_accuracy"].mean(),
            "roc_auc_cv": scores["test_roc_auc"].mean(),
        })

    print("\nScores moyens de validation croisée sur le train :")
    print(pd.DataFrame(results).round(4).to_string(index=False))

    model.fit(X_train, y_train)

    print("\nPipeline entraîné sur le train. Le jeu de test reste réservé.")
    print("Aucun fichier modèle n'a été enregistré à cette étape.")
    return model, X_test, y_test


if __name__ == "__main__":
    trained_model, X_test, y_test = train_model()
    evaluation = evaluate_model(trained_model, X_test, y_test)
