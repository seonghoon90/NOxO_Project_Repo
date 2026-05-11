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

    def buffer_to_df(self) -> pd.DataFrame:
        """deque → DataFrame 변환."""
        return pd.DataFrame(list(self.recent_df_buffer))
