"""미래 시점 단발 예측. Phase 1: 현재 세션 상태 또는 기준점 기반 stub.

추후 시계열 ML 모델로 교체 — `[추후 결정]`.
"""

from datetime import datetime, timedelta, timezone

from app.adapters.predictor import Predictor
from app.core.state_store import StateStore
from app.schemas.prediction import PredictionResponse
from digital_twin.simulation import DEFAULT_CONFIG, ControlVars, DTConfig


class PredictionService:
    def __init__(
        self,
        state_store: StateStore,
        predictor: Predictor,
        dt_config: DTConfig = DEFAULT_CONFIG,
    ) -> None:
        self.state_store = state_store
        self.predictor = predictor
        self.dt_config = dt_config

    def predict(self, target_minutes: int, sid: str | None = None) -> PredictionResponse:
        # 활성 세션이 있으면 그 target을 입력으로 사용, 없으면 기준 운전점
        controls: ControlVars
        if sid and sid in self.state_store:
            state = self.state_store.get(sid)
            assert state is not None
            controls = state.target
        else:
            op = self.dt_config.operating_point
            controls = ControlVars(
                syngas_flow=op.syngas_flow,
                n2_offset=op.n2_offset,
                igv_opening=op.igv_opening,
            )

        output = self.predictor.predict(controls)
        target_time = datetime.now(timezone.utc) + timedelta(minutes=target_minutes)
        threshold = self.dt_config.thresholds.nox_warning_ppm
        return PredictionResponse(
            predicted_nox=round(output.nox, 3),
            target_time=target_time,
            threshold_exceeded=output.nox > threshold,
            threshold_value=threshold,
        )
