"""5분 horizon 단발 NOx 예측 서비스.

`BACKEND_ARCHITECTURE.md §7` `POST /api/prediction` — horizon은 5분 고정.
`DT_ARCHITECTURE.md §7-3` — Sim Loop 상태 참조 X (완전 독립 호출).

입력 경로:
- ML Forecaster: SensorBuffer snapshot(900행) → IGCC 태그명 DataFrame 변환 후 위임.
- Stub Forecaster: 활성 세션 ControlVars(또는 운영점) → features dict로 평탄화.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pandas as pd

from app.adapters.forecaster import Forecaster, ForecastInput
from app.domain.tags import DOMAIN_TO_RAW_TAG
from app.repositories.simulation_log_repo import SimulationLogRepository
from app.schemas.prediction import PredictionResponse
from digital_twin.simulation import DEFAULT_CONFIG, ControlVars, DTConfig

if TYPE_CHECKING:
    from app.core.sensor_buffer import SensorBuffer

# 5분 horizon 고정 — `BACKEND_ARCHITECTURE.md §7`
FORECAST_HORIZON_MINUTES: int = 5


class ForecastService:
    def __init__(
        self,
        sessions: dict,
        forecaster: Forecaster,
        sensor_buffer: "SensorBuffer | None" = None,
        dt_config: DTConfig = DEFAULT_CONFIG,
        simulation_log_repo: SimulationLogRepository | None = None,
    ) -> None:
        self.sessions = sessions
        self.forecaster = forecaster
        self.sensor_buffer = sensor_buffer
        self.dt_config = dt_config
        self.simulation_log_repo = simulation_log_repo

    def predict(self, sid: str | None = None) -> PredictionResponse:
        if self.forecaster.name == "ml":
            recent_df = self._build_recent_df()
            inputs = ForecastInput(recent_df=recent_df)
        else:
            controls = self._resolve_controls(sid)
            inputs = ForecastInput(features=_controls_to_features(controls))

        predicted_nox = self.forecaster.predict(inputs)
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

    def _build_recent_df(self) -> pd.DataFrame:
        """SensorBuffer(도메인 snake_case) → IGCC raw 태그 컬럼 DataFrame.

        SensorBuffer는 normalize_raw_message로 도메인 키를 보유.
        forecaster.predict는 IGCC.* 컬럼명을 요구하므로 DOMAIN_TO_RAW_TAG로 역매핑.
        매핑 외 키는 dropped, 외란 매핑 미완(DISTURBANCE_TAGS 일부 누락) 상태에서도
        503이 아닌 graceful degrade로 운영하기 위해 forecaster 필수 컬럼(RAW_FEATURES +
        TTXM/NOx/DWATT)을 0.0으로 채워준다. 0 폴백이 사용된 컬럼은 모델 정확도를 저하시키지만
        파이프라인은 계속 동작하며, 외란 매핑이 추가되면 자동으로 실데이터로 전환된다.
        """
        if self.sensor_buffer is None or len(self.sensor_buffer) == 0:
            return pd.DataFrame()
        # 지역 import — 모듈 import 순환 방지 + lazy 의존성.
        from digital_twin.forecaster.predict import DWATT_COL, TTXM_COL
        from digital_twin.forecaster.preprocess import NOX_TARGET_COL, RAW_FEATURES

        domain_df = self.sensor_buffer.to_dataframe()
        rename_map = {
            d: r for d, r in DOMAIN_TO_RAW_TAG.items() if d in domain_df.columns
        }
        raw_df = domain_df.rename(columns=rename_map)
        required = set(RAW_FEATURES) | {TTXM_COL, NOX_TARGET_COL, DWATT_COL}
        for col in required - set(raw_df.columns):
            raw_df[col] = 0.0
        return raw_df

    def _resolve_controls(self, sid: str | None) -> ControlVars:
        if sid and sid in self.sessions:
            session = self.sessions[sid]
            if session.control_override is not None:
                return session.control_override
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
    """ControlVars → Stub Forecaster용 features dict (제어 10개 평탄화)."""
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
