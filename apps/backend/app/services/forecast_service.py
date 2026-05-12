"""5분 horizon 단발 NOx 예측 서비스.

`BACKEND_ARCHITECTURE.md §7` `POST /api/prediction` — horizon은 5분 고정.
`DT_ARCHITECTURE.md §7-3` — Sim Loop 상태 참조 X (완전 독립 호출).

활성 세션이 있으면 그 target ControlVars를 입력 피처로 변환하고,
없으면 기준 운전점을 사용한다. 실제 입력 피처 구성은 [추후 결정] —
가안으로 제어 10개 변수를 그대로 features dict에 펼친다.
"""

from datetime import datetime, timedelta, timezone

from app.adapters.forecaster import Forecaster, ForecastInput
from app.core.state_store import StateStore
from app.repositories.simulation_log_repo import SimulationLogRepository
from app.schemas.prediction import PredictionResponse
from digital_twin.simulation import DEFAULT_CONFIG, ControlVars, DTConfig

# 5분 horizon 고정 — `BACKEND_ARCHITECTURE.md §7`
FORECAST_HORIZON_MINUTES: int = 5


class ForecastService:
    def __init__(
        self,
        state_store: StateStore,
        forecaster: Forecaster,
        dt_config: DTConfig = DEFAULT_CONFIG,
        simulation_log_repo: SimulationLogRepository | None = None,
    ) -> None:
        self.state_store = state_store
        self.forecaster = forecaster
        self.dt_config = dt_config
        self.simulation_log_repo = simulation_log_repo

    def predict(self, sid: str | None = None) -> PredictionResponse:
        controls = self._resolve_controls(sid)
        features = _controls_to_features(controls)

        predicted_nox = self.forecaster.predict(ForecastInput(features=features))
        target_time = datetime.now(timezone.utc) + timedelta(minutes=FORECAST_HORIZON_MINUTES)
        threshold = self.dt_config.thresholds.nox_warning_ppm
        response = PredictionResponse(
            predicted_nox=round(predicted_nox, 3),
            target_time=target_time,
            threshold_exceeded=predicted_nox > threshold,
            threshold_value=threshold,
        )
        self._create_forecast_log(response, sid)
        return response

    def _resolve_controls(self, sid: str | None) -> ControlVars:
        if sid and sid in self.state_store:
            state = self.state_store.get(sid)
            assert state is not None
            return state.target
        op = self.dt_config.operating_point
        return ControlVars(
            syngas_flow=op.syngas_flow,
            igv_opening=op.igv_opening,
            n2_offset=op.n2_offset,
            n2_valve_1=op.n2_valve_1,
            syngas_srv=op.syngas_srv,
            syngas_gcv_1=op.syngas_gcv_1,
            syngas_gcv_1a=op.syngas_gcv_1a,
            syngas_gcv_2=op.syngas_gcv_2,
            ibh_valve=op.ibh_valve,
            n2_flow=op.n2_flow,
        )

    def _create_forecast_log(
        self,
        response: PredictionResponse,
        sid: str | None,
    ) -> None:
        if self.simulation_log_repo is None:
            return
        try:
            self.simulation_log_repo.create_forecast_log(response, sid=sid)
        except Exception:
            pass


def _controls_to_features(controls: ControlVars) -> dict[str, float]:
    """ControlVars → Forecaster 입력 피처 dict.

    실제 피처 구성은 [추후 결정]. 가안: 10개 제어 변수를 그대로 펼침.
    """
    return {
        "syngas_flow": controls.syngas_flow,
        "igv_opening": controls.igv_opening,
        "n2_offset": controls.n2_offset,
        "n2_valve_1": controls.n2_valve_1,
        "syngas_srv": controls.syngas_srv,
        "syngas_gcv_1": controls.syngas_gcv_1,
        "syngas_gcv_1a": controls.syngas_gcv_1a,
        "syngas_gcv_2": controls.syngas_gcv_2,
        "ibh_valve": controls.ibh_valve,
        "n2_flow": controls.n2_flow,
    }
