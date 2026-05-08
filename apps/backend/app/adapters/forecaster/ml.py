"""실제 ML 모델 기반 Forecaster — placeholder.

추후 `forecaster_model.pkl` (시계열 5분 horizon 학습 산출물)을 로드하여 채운다.
"""

from app.adapters.forecaster.base import Forecaster, ForecastInput
from app.exceptions import PredictorUnavailableError


class MLForecaster:
    name = "ml"

    def __init__(self, model_path: str = "digital_twin/models/forecaster_model.pkl"):
        self.model_path = model_path
        # TODO: joblib.load 등으로 모델 로드

    def predict(self, inputs: ForecastInput) -> float:
        raise PredictorUnavailableError(
            "ML forecaster not implemented yet — wire forecaster_model.pkl here."
        )
