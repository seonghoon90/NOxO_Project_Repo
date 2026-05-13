"""실제 ML 모델 기반 5분 horizon NOx Forecaster.

digital_twin/forecaster/ (팀원 산출물)에 위임한다.
모델 파일: digital_twin/forecaster/models/forecaster_lgb_model.pkl + metadata.json
파일 부재 시 lifespan이 StubForecaster로 폴백한다.

입력: ForecastInput.recent_df (1초 raw 시계열 DataFrame, IGCC 태그명 컬럼).
출력: 5분 뒤 NOx float.
"""

from __future__ import annotations

from app.adapters.forecaster.base import ForecastInput
from app.exceptions import PredictorUnavailableError

from digital_twin.forecaster import LoadedForecaster, load_model
from digital_twin.forecaster import predict as forecaster_predict


class MLForecaster:
    name = "ml"

    def __init__(self, model_path: str | None = None, metadata_path: str | None = None):
        try:
            self.loaded: LoadedForecaster = load_model(
                model_path=model_path,
                metadata_path=metadata_path,
            )
        except FileNotFoundError as exc:
            raise PredictorUnavailableError(
                f"forecaster model/metadata not found: {exc}"
            ) from exc

    def predict(self, inputs: ForecastInput) -> float:
        if inputs.recent_df is None:
            raise PredictorUnavailableError(
                "MLForecaster.predict requires ForecastInput.recent_df "
                "(IGCC raw tag DataFrame). Got None — check forecast_service wiring."
            )
        return forecaster_predict(self.loaded, recent_df=inputs.recent_df)
