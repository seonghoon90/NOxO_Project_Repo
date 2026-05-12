"""세션별 ML 추론 컨텍스트.

SimulationState(DT 소유)와 별도. 백엔드가 ML 추론에 필요한 인프라(DataFrame/deque)를 보관.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from digital_twin.simulation import OutputVars


@dataclass
class SessionContext:
    sid: str
    plant_context: dict[str, float]      # 외란 29 + TTXM 1 = 30 키 (freeze)
    recent_df_buffer: deque              # maxlen=900, dict rows (RAW 39 + TTXM)
    initial_controls: dict[str, float]   # 스냅샷 시점 제어 10개
    cached_output_target: Optional[OutputVars] = None
    last_ml_call_t: float = 0.0
    last_input_t: float = 0.0
    pending_input_flag: bool = False
    ml_failure_count: int = 0
    _last_gate_reason: str = ""          # "input" | "interval"

    def push_step_row(self, controls_dict: dict[str, float]) -> None:
        """매 sim_step에서 호출. 제어 키 우선, 나머지(외란/TTXM)는 plant_context로 채움."""
        row = {**self.plant_context, **controls_dict}
        self.recent_df_buffer.append(row)

    @classmethod
    def from_snapshot(cls, sid: str, snapshot_df: pd.DataFrame) -> "SessionContext":
        """스냅샷 DataFrame → SessionContext.

        변환:
          - buffer 행: RAW 39 + TTXM 1 = 40 키 (measured_at/NOx/DWATT drop)
          - plant_context: 마지막 행에서 (RAW - CONTROL_TAGS) + TTXM = 30 키
          - initial_controls: 마지막 행의 CONTROL_TAGS 10 키

        외란 매핑 미완 단계에서 누락된 컬럼은 0.0으로 폴백 (DT가 ffill 처리).
        """
        from app.domain.tags import CONTROL_TAGS
        from digital_twin.preprocess import RAW_FEATURES

        TTXM_COL = "IGCC.CC.G1.TTXM"
        BUFFER_COLS = list(RAW_FEATURES) + [TTXM_COL]            # 40
        PLANT_KEYS = [c for c in RAW_FEATURES if c not in CONTROL_TAGS] + [TTXM_COL]  # 30

        df = snapshot_df.copy()
        for col in BUFFER_COLS:
            if col not in df.columns:
                df[col] = 0.0

        last = df.iloc[-1]
        plant_context = {k: float(last[k]) for k in PLANT_KEYS}
        initial_controls = {k: float(last[k]) for k in CONTROL_TAGS}

        buffer = deque(
            (
                {k: float(row[k]) for k in BUFFER_COLS}
                for _, row in df.iterrows()
            ),
            maxlen=900,
        )
        return cls(
            sid=sid,
            plant_context=plant_context,
            recent_df_buffer=buffer,
            initial_controls=initial_controls,
        )

    @classmethod
    def from_sensor_buffer(cls, sid: str, sensor_buffer) -> "SessionContext":
        """SensorBuffer (도메인 snake_case) → SessionContext (원천 태그)."""
        from app.domain.tags import denormalize_to_raw_tags

        df = sensor_buffer.to_dataframe()
        if df.empty:
            raise ValueError("SensorBuffer is empty — bootstrap failed")

        raw_rows = [
            denormalize_to_raw_tags(row.to_dict())
            for _, row in df.iterrows()
        ]
        raw_df = pd.DataFrame(raw_rows)
        return cls.from_snapshot(sid, raw_df)

    def buffer_to_df(self) -> pd.DataFrame:
        """deque → DataFrame 변환."""
        return pd.DataFrame(list(self.recent_df_buffer))
