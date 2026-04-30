"""1차 lag(시간 상수 기반) 동역학 모듈.

[가이드 §5 — 단계 5 "시간 상수 lag 모델 설계"]
- 제어값과 출력값이 즉시 바뀌지 않고 점진적으로 수렴하는 거동을 표현.
- 1차 선형 ODE: dx/dt = (target - x) / τ
- 이산 step 근사:  x_{k+1} = x_k + (target - x_k) * dt / τ
                   = x_k + (1 - exp(-dt/τ)) * (target - x_k)  (정확형)

본 모듈은 의도적으로 dataclass / 외부 라이브러리에 의존하지 않는다.
- 단위 테스트가 단순해지고
- 학습 단계에서 트랜지언트 데이터 증강 시에도 같은 함수 재사용 가능.

사용 가이드:
    from digital_twin.simulation.lag import apply_first_order_lag
    next_temp = apply_first_order_lag(current_temp, target_temp, dt=0.1, tau=10.0)
"""

from __future__ import annotations

import math

from .config import DEFAULT_CONFIG, TimeConstants  # noqa: F401 — re-export

DEFAULT_TIME_CONSTANTS = DEFAULT_CONFIG.time_constants


# ============================================================
# 1) 단순형(Forward Euler) — 가독성 우선
# [가이드 단계 5 — 1차 lag 업데이트 함수]
# ------------------------------------------------------------
# 권장 조건: dt < τ / 5 (수치 안정성 마진)
# dt가 τ에 가까울 때는 정확형(아래)을 사용 권장.
# ============================================================
def apply_first_order_lag(
    current: float,
    target: float,
    dt: float,
    tau: float,
) -> float:
    """Forward Euler 방식 1차 lag.

    Args:
        current: 직전 step의 값.
        target:  수렴 목표값.
        dt:      step 시간(초).
        tau:     시간 상수(초).

    Returns:
        다음 step 값.

    Notes:
        - tau <= 0이면 즉시 target 반환 (lag 없음).
        - dt가 tau보다 크면 oscillation 가능 — 호출 측에서 보장 필요.
    """
    if tau <= 0:
        return target
    return current + (target - current) * dt / tau


# ============================================================
# 2) 정확형(Exact discrete) — 수치 안정성 우선
# [가이드 단계 5 — "곡선이 계단형이 아니라 연속적으로 변화한다" 완료 기준]
# ------------------------------------------------------------
# 1차 ODE의 해석해를 그대로 쓴 형태. dt가 τ에 비해 크더라도
# 수렴값을 절대로 overshoot 하지 않는다 (수치 안정).
# 운영 환경에서는 이 함수를 기본으로 쓰는 것을 권장.
# ============================================================
def apply_first_order_lag_exact(
    current: float,
    target: float,
    dt: float,
    tau: float,
) -> float:
    """정확형 1차 lag (해석해 기반).

    수식:
        x(t+dt) = target + (x(t) - target) * exp(-dt/τ)

    overshoot이 발생하지 않으므로 step 시간(dt)이 큰 경우에 권장.
    """
    if tau <= 0:
        return target
    decay = math.exp(-dt / tau)
    return target + (current - target) * decay


# ============================================================
# 3) 정착 시간 추정 유틸
# [가이드 단계 10 — 트랜지언트 수렴 시간 검증 보조]
# ------------------------------------------------------------
# τ가 주어졌을 때 "값이 목표의 몇 % 까지 수렴하는데 걸리는 시간"을 계산.
# 단계 10의 검증 스크립트에서 사용 예정.
# ============================================================
def settling_time(tau: float, fraction: float = 0.95) -> float:
    """1차 시스템이 fraction 만큼 수렴하는 데 걸리는 시간.

    예: fraction=0.95 → 약 3τ, fraction=0.99 → 약 4.6τ.
    """
    if not 0.0 < fraction < 1.0:
        raise ValueError("fraction must be in (0, 1)")
    return -tau * math.log(1.0 - fraction)
