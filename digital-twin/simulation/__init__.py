"""디지털 트윈 시뮬레이션 패키지.

[가이드 §9 — 본 패키지가 시뮬레이션 코어 진입점]

외부(백엔드/학습 스크립트)에서 사용할 공식 API만 노출한다.
내부 함수/상수는 각 하위 모듈에서 직접 import.

사용 예시:
    # 디렉토리 `digital-twin/`을 sys.path에 추가했다고 가정
    from simulation import sim_step, create_initial_state, ControlVars
    state = create_initial_state(sid="s1", initial_controls=ControlVars(1500, 200, 75), ...)
    state = sim_step(state, predict_fn, config)

import 경로 주의:
    폴더명이 `digital-twin`(하이픈 포함)이라 Python 패키지로 직접 import 불가.
    호출 측에서 `sys.path.insert(0, "<repo>/digital-twin")` 후 `import simulation`
    형태로 사용한다. 백엔드 통합 시점에 폴더명 변경 또는 editable install 결정.
"""

from .engine import (
    DEFAULT_STEP_CONFIG,
    PredictFn,
    StepConfig,
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
    "StepConfig",
    "DEFAULT_STEP_CONFIG",
    "PredictFn",
    # lag
    "apply_first_order_lag",
    "apply_first_order_lag_exact",
    "TimeConstants",
    "DEFAULT_TIME_CONSTANTS",
    "settling_time",
]
