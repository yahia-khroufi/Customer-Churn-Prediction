from pathlib import Path
import hashlib

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, make_scorer, precision_score, recall_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from src.data.preprocess import build_preprocessor, prepare_training_data
from src.utils.logger import get_logger


logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "churn.csv"
RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_FOLDS = 5

PARAM_GRIDS = {
    "LogisticRegression": {
        "classifier__C": [0.01, 0.1, 1.0, 10.0],
        "classifier__class_weight": [None, "balanced"],
    },
    "DecisionTreeClassifier": {
        "classifier__max_depth": [3, 5, 10, None],
        "classifier__min_samples_leaf": [1, 5, 10],
        "classifier__class_weight": [None, "balanced"],
    },
    "RandomForestClassifier": {
        "classifier__n_estimators": [100, 200],
        "classifier__max_depth": [None, 10],
        "classifier__min_samples_leaf": [1, 5],
        "classifier__class_weight": [None, "balanced"],
    },
    "XGBClassifier": {
        "classifier__n_estimators": [100, 200],
        "classifier__max_depth": [3, 4, 5],
        "classifier__learning_rate": [0.05, 0.1],
    },
}


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

    # Chaque modèle possède son preprocessing, appris dans chaque pli du train.
    classifiers = {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        "DecisionTreeClassifier": DecisionTreeClassifier(random_state=RANDOM_STATE),
        "RandomForestClassifier": RandomForestClassifier(
            n_estimators=200, random_state=RANDOM_STATE, n_jobs=1,
        ),
        "XGBClassifier": XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.1,
            objective="binary:logistic", eval_metric="logloss",
            random_state=RANDOM_STATE, n_jobs=1,
        ),
    }
    models = {}
    for name, classifier in classifiers.items():
        models[name] = Pipeline([
            ("preprocessor", build_preprocessor(scale_numeric=name == "LogisticRegression")),
            ("classifier", classifier),
        ])

    cv = StratifiedKFold(
        n_splits=CV_FOLDS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )
    scoring = {
        "accuracy": "accuracy",
        "precision": make_scorer(precision_score, zero_division=0),
        "recall": make_scorer(recall_score, zero_division=0),
        "f1": make_scorer(f1_score, zero_division=0),
    }

    results = []

    for name, candidate in models.items():

        logger.info("Validation croisée du modèle : %s", name)

        scores = cross_validate(
            candidate,
            X_train,
            y_train,
            cv=cv,
            scoring=scoring,
            error_score="raise",
        )

        results.append({
            "modele": name,
            "accuracy_cv": scores["test_accuracy"].mean(),
            "precision_cv": scores["test_precision"].mean(),
            "recall_cv": scores["test_recall"].mean(),
            "f1_cv": scores["test_f1"].mean(),
            "f1_std": scores["test_f1"].std(),
        })

    results_df = pd.DataFrame(results).sort_values(
        "f1_cv", ascending=False, kind="stable",
    )

    logger.info(
        "Scores moyens de validation croisée :\n%s",
        results_df.round(4).to_string(index=False),
    )

    top_models = results_df.head(2)["modele"].tolist()
    logger.info("Modèles retenus pour le réglage : %s", ", ".join(top_models))
    searches = {}
    tuned_results = []
    search_trials = {}

    for name in top_models:
        logger.info("Recherche d'hyperparamètres pour : %s", name)
        search = GridSearchCV(
            estimator=models[name],
            param_grid=PARAM_GRIDS[name],
            scoring=scoring,
            refit="f1",
            cv=cv,
            n_jobs=1,
            error_score="raise",
        )
        search.fit(X_train, y_train)
        searches[name] = search
        search_trials[name] = [
            {"params": params, "f1_cv": float(search.cv_results_["mean_test_f1"][i])}
            for i, params in enumerate(search.cv_results_["params"])
        ]

        best_index = search.best_index_
        tuned_results.append({
            "modele": name,
            "accuracy_cv": search.cv_results_["mean_test_accuracy"][best_index],
            "precision_cv": search.cv_results_["mean_test_precision"][best_index],
            "recall_cv": search.cv_results_["mean_test_recall"][best_index],
            "f1_cv": search.cv_results_["mean_test_f1"][best_index],
            "f1_std": search.cv_results_["std_test_f1"][best_index],
        })
        logger.info("Meilleurs paramètres pour %s : %s", name, search.best_params_)

    tuned_df = pd.DataFrame(tuned_results).sort_values(
        "f1_cv", ascending=False, kind="stable",
    )
    logger.info(
        "Résultats après réglage :\n%s",
        tuned_df.round(4).to_string(index=False),
    )

    best_name = tuned_df.iloc[0]["modele"]
    model = searches[best_name].best_estimator_
    model.training_summary_ = {
        "selected_model": best_name,
        "selection_metric": "f1",
        "best_params": searches[best_name].best_params_,
        "baseline_results": results_df.to_dict(orient="records"),
        "tuned_results": tuned_df.to_dict(orient="records"),
        "search_trials": search_trials,
        "random_state": RANDOM_STATE,
        "cv_folds": CV_FOLDS,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "dataset_sha256": hashlib.sha256(Path(data_path).read_bytes()).hexdigest(),
    }
    logger.info("meilleur model on bason sur f1-score de cross vlue: %s", best_name)
    logger.info("meilleurs parametres  finaux : %s", searches[best_name].best_params_)
    logger.info("Le meilleur pipeline a été réentraîné sur tout le train")

    return model, X_test, y_test


if __name__ == "__main__":
    trained_model, X_test, y_test = train_model()
