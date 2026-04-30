"""디지털 트윈 시뮬레이션 패키지.

[가이드 §9 — 본 패키지가 시뮬레이션 코어 진입점]

외부(백엔드/학습 스크립트)에서 사용할 공식 API만 노출한다.
내부 함수/상수는 각 하위 모듈에서 직접 import.

사용 예시:
    # repo 루트가 PYTHONPATH에 있다고 가정 (Docker / pytest.ini로 자동 처리됨)
    from digital_twin.simulation import sim_step, create_initial_state, ControlVars
    state = create_initial_state(sid="s1", initial_controls=ControlVars(1500, 200, 75), ...)
    state = sim_step(state, predict_fn, config)
"""

from .config import (
    DEFAULT_CONFIG,
    DTConfig,
)
from .engine import (
    PredictFn,
    create_initial_state,
    sim_step,
)
from .lag import (
    DEFAULT_TIME_CONSTANTS,
    TimeConstants,
    apply_first_order_lag,
    apply_first_order_lag_exact,
    settling_time,
)
from .state import (
    ControlVars,
    OutputVars,
    SimulationState,
)

__all__ = [
    # 상태 객체
    "ControlVars",
    "OutputVars",
    "SimulationState",
    # 엔진
    "sim_step",
    "create_initial_state",
    "PredictFn",
    # 설정
    "DTConfig",
    "DEFAULT_CONFIG",
    # lag
    "apply_first_order_lag",
    "apply_first_order_lag_exact",
    "TimeConstants",
    "DEFAULT_TIME_CONSTANTS",
    "settling_time",
]
