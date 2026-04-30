from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.domain.tags import ControlVars, OutputVars


@dataclass
class SimulationState:
    """세션의 현재 시뮬 상태. Sim Loop가 매 step마다 mutate."""

    sid: str
    t: float = 0.0  # 시뮬 경과 시간 (초)

    # 제어 입력 — 사용자 조작 → target. 현재값은 lag 모델로 점진 수렴.
    target: ControlVars = field(default_factory=lambda: ControlVars(1500.0, 200.0, 75.0))
    current: ControlVars = field(default_factory=lambda: ControlVars(1500.0, 200.0, 75.0))

    # 출력 — Predictor가 산출한 정상상태 target과 lag 적용된 현재값
    output_target: OutputVars = field(
        default_factory=lambda: OutputVars(
            nox=20.0, co=10.0, flame_temp=1450.0, lambda_=1.1, power=248.6
        )
    )
    output: OutputVars = field(
        default_factory=lambda: OutputVars(
            nox=20.0, co=10.0, flame_temp=1450.0, lambda_=1.1, power=248.6
        )
    )

    warning: bool = False
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
