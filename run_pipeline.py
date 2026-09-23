
import argparse

from src.models.evaluate import evaluate_model
from src.models.persistence import save_model_metadata, save_pipeline
from src.models.tracking import track_experiment
from src.models.train import train_model
from src.utils.logger import get_logger


logger = get_logger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Comparer et régler les modèles de Customer Churn.",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Évaluer le modèle retenu sur le test réservé, puis sauvegarder le pipeline.",
    )
    parser.add_argument("--track", action="store_true", help="Enregistrer cette expérience et le modèle dans MLflow.")
    args = parser.parse_args(argv)

    model, X_test, y_test = train_model()

    evaluation = None
    model_path = None
    if args.evaluate:
        evaluation = evaluate_model(model, X_test, y_test)
        model_path = save_pipeline(model)
        save_model_metadata(model, model_path, evaluation, len(y_test))
    else:
        logger.info(
           '''
             entrainment terminee pour lancer evaluate tu peut faire 
             python run_pipeline.py --evaluate
            '''
        )

    if args.track:
        run_id = track_experiment(model, evaluation, model_path)
        logger.info("Expérience MLflow enregistrée : %s", run_id)


if __name__ == "__main__":
    main()
