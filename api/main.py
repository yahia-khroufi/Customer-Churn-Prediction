from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.schemas import CustomerInput, PredictionOutput
from src.common.data_contract import CATEGORY_VALUES, FEATURE_COLUMNS
from src.models.persistence import DEFAULT_MODEL_PATH
from src.models.predict import ChurnPredictor


logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(model_path: str | Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.predictor = None
        try:
            path = model_path or os.environ.get("MODEL_PATH") or DEFAULT_MODEL_PATH
            app.state.predictor = ChurnPredictor(path)
        except Exception:
            logger.exception("Impossible de charger le pipeline")
        yield
        app.state.predictor = None

    app = FastAPI(title="Customer Churn API", version="1.0.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health")
    def health(request: Request):
        ready = getattr(request.app.state, "predictor", None) is not None
        return JSONResponse(
            status_code=200 if ready else 503,
            content={"status": "ok" if ready else "unavailable", "model_loaded": ready},
        )

    @app.get("/schema")
    def schema():
        return {"features": FEATURE_COLUMNS, "categories": CATEGORY_VALUES}

    @app.get("/model-info")
    def model_info(request: Request):
        predictor = getattr(request.app.state, "predictor", None)
        if predictor is None:
            raise HTTPException(503, "Le modèle est indisponible.")
        metadata = predictor.metadata
        return {
            "model_name": predictor.model_name,
            "feature_count": len(FEATURE_COLUMNS),
            "test_samples": metadata.get("test_samples"),
            "evaluation": metadata.get("evaluation"),
            "created_at": metadata.get("created_at"),
        }

    @app.post("/predict", response_model=PredictionOutput)
    def predict(customer: CustomerInput, request: Request):
        predictor = getattr(request.app.state, "predictor", None)
        if predictor is None:
            raise HTTPException(503, "Le modèle est indisponible. Réessayer plus tard.")
        try:
            return predictor.predict(customer.model_dump())
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    return app


app = create_app()
