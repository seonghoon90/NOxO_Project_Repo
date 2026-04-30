"""하이브리드 시뮬레이션 엔진 — sim_step 통합.

[가이드 §5 — 단계 6 "하이브리드 시뮬레이션 엔진 조립"]
[가이드 §11 — 본 모듈이 프로젝트 디지털 트윈의 "운영 의사결정 엔진" 코어]

본 모듈은 features / lag / chemistry / (외부) ML predictor 4개 빌딩 블록을
한 번의 step 함수로 통합한다. 가이드 §6 "내부 처리 순서"를 코드로 옮긴 형태:

    1. 입력 queue에서 최신 제어 목표값 반영      ── 호출 측에서 state.target 갱신 후 진입
    2. fuel/n2/igv를 lag로 갱신                  ── lag.apply_first_order_lag
    3. λ 계산                                    ── features.compute_lambda
    4. ML로 정상상태 화염온도/NOx target 계산    ── 외부에서 주입된 predict_fn
    5. 화염온도를 lag로 갱신                     ── lag.apply_first_order_lag
    6. Zeldovich ODE로 NOx 생성량 계산           ── chemistry.integrate_zeldovich_step
    7. CO/효율 계산                              ── features.compute_co / compute_efficiency
    8. 임계치 비교와 warning 갱신                ── settings.nox_threshold_ppm 비교

설계 결정:
- ML 호출은 의존성 역전을 위해 함수 인자(`predict_fn`)로 받는다.
  → DT 단독 단위 테스트 시 stub 함수만 주입하면 됨.
  → 실제 운영에선 backend의 Predictor가 주입됨.
- 본 모듈은 asyncio / FastAPI / WebSocket을 모르는 순수 함수.
  → backend `core/sim_loop.py`가 본 모듈을 감싸는 얇은 래퍼 역할만 담당.

향후 백엔드와의 통합 경로 [가이드 §9 권장]:
- backend `app/core/sim_loop.py::SimLoopManager._step` 내부 로직을
  본 모듈의 `sim_step`을 호출하는 형태로 점진 교체.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from . import chemistry, features
from .lag import (
    DEFAULT_TIME_CONSTANTS,
    TimeConstants,
    apply_first_order_lag_exact,
)
from .state import (
    ControlVars,
    OutputVars,
    SimulationState,
)


# ============================================================
# step 설정값
# [가이드 §3 / DT_PRD §5 — 100~500ms 주기, step < 50ms 목표]
# ============================================================
@dataclass(frozen=True)
class StepConfig:
    """sim_step 호출 시 사용할 설정값 묶음."""

    dt: float = 0.2  # step 시간(초). backend `sim_dt_seconds`와 일치시킬 것.

    # 시간 상수 (lag.py와 동일 단위/의미)
    time_constants: TimeConstants = DEFAULT_TIME_CONSTANTS

    # NOx 임계치 [조사 필요]
    nox_threshold_ppm: float = 50.0

    # Zeldovich 결과를 ML target에 가중합할 비율 (0=ML만, 1=Zeldovich만)
    # [추후 결정] 실측 검증 후 튜닝
    physics_blend_ratio: float = 0.0


DEFAULT_STEP_CONFIG = StepConfig()


# ============================================================
# Predictor 인터페이스 — Callable 타입 별칭
# [가이드 단계 4 — 정상상태 ML 회귀 모델의 추론 진입점]
# ------------------------------------------------------------
# backend의 `app.adapters.predictor.base.Predictor`와 호환되도록
# 동일한 시그니처(ControlVars → OutputVars)를 채택.
# DT 모듈은 backend에 의존하지 않기 위해 Protocol 대신 Callable 타입만 노출.
# ============================================================
PredictFn = Callable[[ControlVars], OutputVars]


# ============================================================
# 메인 step 함수
# [가이드 §6 — sim_step / 단계 6 통합]
# ============================================================
def sim_step(
    state: SimulationState,
    predict_fn: PredictFn,
    config: StepConfig = DEFAULT_STEP_CONFIG,
) -> SimulationState:
    """디지털 트윈의 단일 step 진행.

    호출 전 조건:
        - state.target 이 호출 측에서 최신 사용자 입력으로 갱신되어 있어야 함.
          (가이드 §6 내부 처리 순서 1번 — 본 함수 외부에서 처리)

    Args:
        state:      현재 SimulationState (in-place mutate).
        predict_fn: ControlVars → OutputVars 매핑 함수.
                    프로토타입에서는 backend StubPredictor 또는 MLPredictor.
        config:     step 설정.

    Returns:
        갱신된 state (동일 객체, 편의를 위해 반환).
    """
    dt = config.dt
    tau = config.time_constants

    # ----------------------------------------------------------
    # [Step 2] 제어 변수 lag — target → current 점진 수렴
    # 가이드 §6 내부 처리 순서 2번
    # ----------------------------------------------------------
    state.current = ControlVars(
        syngas_flow=apply_first_order_lag_exact(
            state.current.syngas_flow, state.target.syngas_flow, dt, tau.fuel
        ),
        n2_offset=apply_first_order_lag_exact(
            state.current.n2_offset, state.target.n2_offset, dt, tau.n2
        ),
        igv_opening=apply_first_order_lag_exact(
            state.current.igv_opening, state.target.igv_opening, dt, tau.igv
        ),
    )

    # ----------------------------------------------------------
    # [Step 3] 즉시 계산 파생값 — 공기비 λ
    # 가이드 §6 내부 처리 순서 3번
    # ----------------------------------------------------------
    lambda_now = features.compute_lambda(
        syngas_flow=state.current.syngas_flow,
        n2_offset=state.current.n2_offset,
        igv_opening=state.current.igv_opening,
    )

    # ----------------------------------------------------------
    # [Step 4] ML 추론으로 정상상태 출력 target 계산
    # 가이드 §6 내부 처리 순서 4번 / 단계 4 ML 회귀
    # ----------------------------------------------------------
    # Predictor는 ControlVars → OutputVars 형태. λ는 Predictor 내부에서
    # 자체 계산한 값을 쓸 수도 있고, 외부에서 주입한 값을 쓸 수도 있다.
    # 프로토타입에서는 Predictor 내부 계산을 신뢰하되, λ는 features 모듈의
    # 결과로 덮어써서 단일 진실원을 features.py로 일원화한다.
    ml_output = predict_fn(state.current)
    state.output_target = OutputVars(
        nox=ml_output.nox,
        co=ml_output.co,
        flame_temp=ml_output.flame_temp,
        lambda_=lambda_now,           # features 결과로 덮어쓰기
        efficiency=ml_output.efficiency,
        power=ml_output.power,
    )

    # ----------------------------------------------------------
    # [Step 5] 화염 온도 lag — 출력 lag 영역 시작
    # 가이드 §6 내부 처리 순서 5번
    # ----------------------------------------------------------
    flame_temp_next = apply_first_order_lag_exact(
        state.output.flame_temp,
        state.output_target.flame_temp,
        dt,
        tau.temp,
    )

    # ----------------------------------------------------------
    # [Step 6] Zeldovich ODE로 NOx 적분
    # 가이드 §6 내부 처리 순서 6번 / 단계 3 물리 베이스라인
    # ----------------------------------------------------------
    # ML이 산출한 정상상태 NOx target과 별개로,
    # 물리 모델로도 NOx를 적분해 nox_integrated에 누적한다.
    # 추후 두 결과를 physics_blend_ratio로 가중합하여 최종 NOx 결정.
    o2_frac = features.compute_o2_fraction(lambda_now)
    n2_frac = features.compute_n2_fraction(lambda_now, state.current.n2_offset)

    state.nox_integrated = chemistry.integrate_zeldovich_step(
        nox_current=state.nox_integrated,
        flame_temp_k=flame_temp_next,
        o2_fraction=o2_frac,
        n2_fraction=n2_frac,
        dt=dt,
    )

    # NOx 출력값: ML lag 결과와 Zeldovich 적분 결과의 가중합
    # [추후 결정] blend_ratio는 실측 캘리브레이션 후 결정
    nox_lag = apply_first_order_lag_exact(
        state.output.nox,
        state.output_target.nox,
        dt,
        tau.nox,
    )
    nox_blended = (
        (1.0 - config.physics_blend_ratio) * nox_lag
        + config.physics_blend_ratio * state.nox_integrated
    )

    # ----------------------------------------------------------
    # [Step 7] CO / 효율 계산
    # 가이드 §6 내부 처리 순서 7번 / 단계 2 파생 피처
    # ----------------------------------------------------------
    co_lag = apply_first_order_lag_exact(
        state.output.co,
        state.output_target.co,
        dt,
        tau.co,
    )

    efficiency_now = features.compute_efficiency(
        syngas_flow=state.current.syngas_flow,
        flame_temp=flame_temp_next,
    )

    power_lag = apply_first_order_lag_exact(
        state.output.power,
        state.output_target.power,
        dt,
        tau.power,
    )

    state.output = OutputVars(
        nox=nox_blended,
        co=co_lag,
        flame_temp=flame_temp_next,
        lambda_=lambda_now,
        efficiency=efficiency_now,
        power=power_lag,
    )

    # ----------------------------------------------------------
    # [Step 8] 임계치 비교 & 메타 업데이트
    # 가이드 §6 내부 처리 순서 8번
    # ----------------------------------------------------------
    state.warning = state.output.nox > config.nox_threshold_ppm
    state.t += dt
    state.step_count += 1
    state.last_updated = datetime.now(timezone.utc)

    return state


# ============================================================
# 헬퍼: 새 시뮬 세션 초기 상태 생성
# [가이드 단계 7 — 세션 시작 API의 초기 운전 조건 적용]
# ============================================================
def create_initial_state(
    sid: str,
    initial_controls: ControlVars,
    predict_fn: PredictFn,
) -> SimulationState:
    """초기 운전점에서 정상상태 출력으로 미리 채워진 상태 생성.

    사용자가 세션을 시작할 때 t=0 시점의 state는 비어 있으면 안 되고,
    초기 운전점에 대응하는 정상상태 출력값으로 미리 셋업되어야 한다
    (가이드 §6 — "상태 전이가 순차적이며 재현 가능하다" 완료 기준).
    """
    initial_output = predict_fn(initial_controls)
    lambda_init = features.compute_lambda(
        syngas_flow=initial_controls.syngas_flow,
        n2_offset=initial_controls.n2_offset,
        igv_opening=initial_controls.igv_opening,
    )

    output_with_lambda = OutputVars(
        nox=initial_output.nox,
        co=initial_output.co,
        flame_temp=initial_output.flame_temp,
        lambda_=lambda_init,
        efficiency=features.compute_efficiency(
            initial_controls.syngas_flow, initial_output.flame_temp
        ),
        power=initial_output.power,
    )

    return SimulationState(
        sid=sid,
        target=initial_controls,
        current=initial_controls,
        output_target=output_with_lambda,
        output=output_with_lambda,
        nox_integrated=initial_output.nox,
    )
