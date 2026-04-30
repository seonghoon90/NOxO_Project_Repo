"""디지털 트윈 시뮬레이션 상태 객체.

[가이드 §6 / §7 — 단계 6 "하이브리드 시뮬레이션 엔진 조립"의 상태 정의 영역]
이 파일은 시뮬 루프가 매 step마다 mutate 하는 단일 진실원(SoT)이다.
백엔드 `apps/backend/app/domain/simulation.py`의 SimulationState와
의미상 동일하지만, DT는 백엔드 의존 없이 단독 테스트 가능해야 하므로
여기서 별도로 정의한다. 추후 두 정의를 한쪽으로 통일하는 것은
[추후 결정] 사항이다.

설계 원칙:
- "사용자 목표값(target)"과 "현재 동적 상태(current)"를 항상 분리한다.
  → 가이드 §5 단계 5의 1차 lag 동역학을 구현하기 위한 핵심 구조.
- 정상상태 ML 회귀가 산출한 출력 target(`output_target`)도 별도 보관.
  → 가이드 §6 내부 처리 순서 4번(ML 추론) 결과를 보관하는 슬롯.
- ODE 적분 누적값(`nox_integrated`) 같은 물리 적분 변수는 lag 변수와
  분리해 둔다. lag와 ODE는 의미가 다른 동역학이라 섞으면 검증이 어렵다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .config import DEFAULT_CONFIG

_OP = DEFAULT_CONFIG.operating_point
_IO = DEFAULT_CONFIG.initial_output


# ============================================================
# 제어 입력 변수 (사용자 → DT)
# [가이드 §3 핵심 입력 / 단계 0 변수 사전]
# ------------------------------------------------------------
# 컬럼명 매핑은 백엔드 `app/domain/tags.py`에서 IGCC 태그와 1:1 대응.
# DT 단독 모듈에서는 의미 단위 이름만 노출한다.
# ============================================================
@dataclass(frozen=True)
class ControlVars:
    """제어 입력 — 단일 step에 적용될 운전 목표값.

    Attributes:
        syngas_flow: 합성가스 유량. 단위는 [추후 결정] (가안: kg/h 또는 Nm3/h).
        n2_offset:   희석질소 유량 오프셋. NOx 저감을 위한 lean 운전 보조.
        igv_opening: 가스터빈 IGV(입구 가이드 베인) 개도(%).
                     공기 유량을 직접 제어하므로 공기비 λ에 1차적 영향.
    """

    syngas_flow: float
    n2_offset: float
    igv_opening: float


# ============================================================
# 출력 변수 (DT → 백엔드/프론트)
# [가이드 §3 핵심 출력 / 단계 6 step 산출물]
# ------------------------------------------------------------
# - nox/co/exhaust_temp: lag 모델로 점진 수렴하는 동적 변수
# - lambda_:           즉시 계산값 (lag 미적용)
# - efficiency:        파생 계산값
# ============================================================
@dataclass(frozen=True)
class OutputVars:
    """모델 산출 변수.

    Attributes:
        nox:        NOx 농도. 단위 가안 [ppm]. Zeldovich + ML 하이브리드 결과.
        co:         CO 농도. 단위 가안 [ppm]. λ에 강하게 의존.
        exhaust_temp: 배기 온도. IGCC.CC.G1.TTXM 실측값 기반. 단위 [°C].
        lambda_:    공기비(λ). 무차원. λ=1이 stoichiometric.
        efficiency: 발전 효율. 무차원(0~1) 또는 % [추후 결정].
        power:      발전량 [MW]. (추후 정상상태 ML 회귀로 산출)
    """

    nox: float
    co: float
    exhaust_temp: float
    lambda_: float
    efficiency: float
    power: float


# ============================================================
# 시뮬레이션 상태 — Sim Loop가 매 step mutate
# [가이드 §6 — 상태 객체 정의]
# ============================================================
@dataclass
class SimulationState:
    """세션 단위 시뮬 상태. 단일 step의 입출력 모두를 보관한다.

    상태 분리 원칙:
        target          : 사용자가 방금 누른 값 (즉시 반영되는 목표)
        current         : lag 적용된 실제 현재 운전점
        output_target   : ML이 예측한 정상상태 출력값 (lag의 목표)
        output          : lag 적용된 현재 출력값 (UI에 표시되는 값)
    """

    sid: str
    t: float = 0.0  # 시뮬 경과 시간 [초]

    # ---- 제어 변수: target → (lag) → current ----
    # [가이드 단계 5 "lag 모델"의 입력 lag 영역]
    target: ControlVars = field(
        default_factory=lambda: ControlVars(_OP.syngas_flow, _OP.n2_offset, _OP.igv_opening)
    )
    current: ControlVars = field(
        default_factory=lambda: ControlVars(_OP.syngas_flow, _OP.n2_offset, _OP.igv_opening)
    )

    # ---- 출력 변수: ML 추론 → output_target → (lag/ODE) → output ----
    # [가이드 단계 4 ML 회귀 결과 보관 + 단계 5 출력 lag 영역]
    output_target: OutputVars = field(
        default_factory=lambda: OutputVars(
            nox=_IO.nox,
            co=_IO.co,
            exhaust_temp=_IO.exhaust_temp,
            lambda_=_IO.lambda_,
            efficiency=_IO.efficiency,
            power=_IO.power,
        )
    )
    output: OutputVars = field(
        default_factory=lambda: OutputVars(
            nox=_IO.nox,
            co=_IO.co,
            exhaust_temp=_IO.exhaust_temp,
            lambda_=_IO.lambda_,
            efficiency=_IO.efficiency,
            power=_IO.power,
        )
    )

    # ---- ODE 적분 누적 변수 ----
    # [가이드 단계 3 — Zeldovich ODE의 적분 결과를 별도 보관]
    # NOx 최종값은 lag/ODE 둘 중 하나의 동역학을 선택하거나
    # 두 결과를 가중합할 수 있게 분리 저장한다.
    nox_integrated: float = field(default_factory=lambda: _IO.nox_integrated)

    # ---- 메타데이터 ----
    last_updated: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    warning: bool = False  # NOx 임계치 초과 플래그 [조사 필요] 임계치 출처

    # ---- step 카운터 (디버깅/관측용) ----
    step_count: int = 0
