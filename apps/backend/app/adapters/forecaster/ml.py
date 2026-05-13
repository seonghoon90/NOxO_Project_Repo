"""실제 ML 모델 기반 5분 horizon NOx Forecaster.

모델 파일: digital_twin/models/forecaster_model.pkl (모델링 팀 산출물)
파일 부재 시 lifespan이 StubForecaster로 폴백한다.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from app.adapters.forecaster.base import ForecastInput
from app.exceptions import PredictorUnavailableError


class MLForecaster:
    name = "ml"

    def __init__(self, model_path: str = "digital_twin/models/forecaster_model.pkl"):
        self.model_path = Path(model_path)
        try:
            self.model = joblib.load(self.model_path)
        except FileNotFoundError as exc:
            raise PredictorUnavailableError(
                f"forecaster model not found: {self.model_path}"
            ) from exc

    def predict(self, inputs: ForecastInput) -> float:
        """features dict → 5분 후 NOx float."""
        features_df = pd.DataFrame([inputs.features])
        prediction = self.model.predict(features_df)
        return float(prediction[0])
