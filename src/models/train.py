from pathlib import Path

import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline

from src.common.data_contract import ID_COLUMN
from src.data.preprocess import build_preprocessor, prepare_training_data
from src.models.evaluate import evaluate_model
from src.utils.logger import get_logger


logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "churn.csv"
RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_FOLDS = 5


def train_model(
    data_path: str | Path = DATA_PATH,
) -> tuple[Pipeline, pd.DataFrame, pd.Series]:

    logger.info("Chargement des données depuis %s", data_path)

    df = pd.read_csv(data_path)

    logger.info("Préparation des données d'entraînement")

    X, y = prepare_training_data(df)

    if y.nunique() != 2:
        raise ValueError(
            "L'entraînement nécessite les deux classes : No et Yes."
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    if y_train.value_counts().min() < CV_FOLDS:
        raise ValueError(
            "Le train doit contenir au moins 5 clients de chaque classe."
        )

    logger.info("Clients d'entraînement : %d", len(X_train))
    logger.info("Clients réservés au test : %d", len(X_test))

    baseline = Pipeline([
        ("preprocessor", build_preprocessor(scale_numeric=True)),
        ("classifier", DummyClassifier(strategy="most_frequent")),
    ])

    model = Pipeline([
        ("preprocessor", build_preprocessor(scale_numeric=True)),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                random_state=RANDOM_STATE,
            ),
        ),
    ])

    cv = StratifiedKFold(
        n_splits=CV_FOLDS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )

    results = []

    for name, candidate in [
        ("Classe majoritaire", baseline),
        ("LogisticRegression", model),
    ]:

        logger.info("Validation croisée du modèle : %s", name)

        scores = cross_validate(
            candidate,
            X_train,
            y_train,
            cv=cv,
            scoring={
                "accuracy": "accuracy",
                "roc_auc": "roc_auc",
            },
            error_score="raise",
        )

        results.append({
            "modele": name,
            "accuracy_cv": scores["test_accuracy"].mean(),
            "roc_auc_cv": scores["test_roc_auc"].mean(),
        })

    results_df = pd.DataFrame(results).round(4)

    logger.info(
        "Scores moyens de validation croisée :\n%s",
        results_df.to_string(index=False),
    )

    logger.info("Entraînement final de LogisticRegression")

    model.fit(X_train, y_train)

    logger.info("Pipeline entraîné avec succès")
    logger.info("Le jeu de test reste réservé à l'évaluation finale")
    logger.info("Aucun modèle n'a été enregistré à cette étape")

    return model, X_test, y_test


if __name__ == "__main__":
    trained_model, X_test, y_test = train_model()

    