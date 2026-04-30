"""미래 시점 단발 예측. Phase 1: 현재 세션 상태 또는 기준점 기반 stub.

추후 시계열 ML 모델로 교체 — `[추후 결정]`.
"""

from datetime import datetime, timedelta, timezone

from app.adapters.predictor import Predictor
from app.config import Settings
from app.core.state_store import StateStore
from app.domain.tags import ControlVars
from app.schemas.prediction import PredictionResponse


class PredictionService:
    def __init__(
        self,
        settings: Settings,
        state_store: StateStore,
        predictor: Predictor,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.predictor = predictor

    def predict(self, target_minutes: int, sid: str | None = None) -> PredictionResponse:
        # 활성 세션이 있으면 그 target을 입력으로 사용, 없으면 기본 운전점
        controls: ControlVars
        if sid and sid in self.state_store:
            state = self.state_store.get(sid)
            assert state is not None
            controls = state.target
        else:
            controls = ControlVars(syngas_flow=1500.0, n2_offset=200.0, igv_opening=75.0)

        output = self.predictor.predict(controls)
        target_time = datetime.now(timezone.utc) + timedelta(minutes=target_minutes)
        threshold = self.settings.nox_threshold_ppm
        return PredictionResponse(
            predicted_nox=round(output.nox, 3),
            target_time=target_time,
            threshold_exceeded=output.nox > threshold,
            threshold_value=threshold,
        )
