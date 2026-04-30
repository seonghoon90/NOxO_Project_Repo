"""물리 기반 NOx 계산 — Zeldovich 메커니즘.

[가이드 §5 — 단계 3 "물리 기반 NOx 계산 베이스라인 구축"]
- Thermal NOx의 지배 메커니즘인 확장 Zeldovich 반응을 단순화하여 구현.
- 정확한 화학 반응 모델은 Cantera 등 외부 라이브러리가 필요하지만,
  본 프로토타입은 실시간성을 우선시해 1개 미분방정식 근사로 시작한다.
- 추후 Cantera surrogate 도입은 [추후 결정] 사항.

확장 Zeldovich 메커니즘 (요약):
    R1: O + N2 -> NO + N
    R2: N + O2 -> NO + O
    R3: N + OH -> NO + H

NO 생성률(반응이 정방향 우세할 때):
    d[NO]/dt ≈ 2 * k1(T) * [O][N2]

여기서 k1(T)는 Arrhenius 형태의 강한 온도 의존:
    k1(T) = A * exp(-Ea / (R * T))
    A  : pre-exponential factor   [조사 필요]
    Ea : activation energy        [조사 필요]
    R  : 기체상수 (8.314 J/mol/K)

본 모듈은 위 식을 step 단위로 계산해 NOx 생성률을 반환한다.
적분기는 가이드 §10에서 [Euler / RK4 / scipy.integrate] 중 선택 예정.
프로토타입에서는 Forward Euler로 시작.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# ============================================================
# Zeldovich 반응 상수 — [조사 필요] 합성가스 적합값
# [가이드 §3 / DT_ARCHITECTURE §15 — Zeldovich 반응 상수 합성가스 적합값]
# ------------------------------------------------------------
# 아래 값은 일반 메탄 연소 문헌값 가안. 합성가스(H2/CO 위주) 적합값으로
# 교체 필요. 단위/스케일 모두 [조사 필요] 마커 영역.
# ============================================================
@dataclass(frozen=True)
class ZeldovichConstants:
    """Arrhenius 형태 반응 상수 묶음."""

    # k1: O + N2 -> NO + N의 정방향 속도상수
    pre_exponential_A: float = 1.8e8     # [m^3/(mol·s)] 가안
    activation_energy_Ea: float = 318000.0  # [J/mol] 가안 (~76 kcal/mol)

    # 보편 기체 상수
    gas_constant_R: float = 8.314        # [J/(mol·K)]

    # 비물리적 폭주 방지를 위한 상한값
    max_nox_rate_ppm_per_s: float = 50.0  # [조사 필요] 임계 폭주 방지


DEFAULT_ZELDOVICH = ZeldovichConstants()


# ============================================================
# 1) Arrhenius 속도상수 계산
# [가이드 단계 3 — Zeldovich 반응률 함수의 구성 요소]
# ============================================================
def arrhenius_rate_constant(
    temperature_k: float,
    consts: ZeldovichConstants = DEFAULT_ZELDOVICH,
) -> float:
    """k(T) = A * exp(-Ea / (R*T))

    Args:
        temperature_k: 화염 온도 [K]. 양수여야 함.
        consts:        Arrhenius 상수 묶음.

    Returns:
        반응 속도 상수. 단위는 입력 상수에 의존.

    Notes:
        - 1500K 부근에서 급격히 증가 (Thermal NOx의 특징)
        - 1300K 미만에서는 거의 0
    """
    if temperature_k <= 0:
        return 0.0
    exponent = -consts.activation_energy_Ea / (consts.gas_constant_R * temperature_k)
    # underflow 방지: exp 인자가 너무 작으면 0 반환
    if exponent < -700.0:
        return 0.0
    return consts.pre_exponential_A * math.exp(exponent)


# ============================================================
# 2) NOx 생성률 계산 (단위 시간당)
# [가이드 단계 3 — Zeldovich ODE 우변]
# ------------------------------------------------------------
# d[NO]/dt = 2 * k1(T) * [O] * [N2]
#
# 프로토타입 단순화:
#   - [O] (산소 원자 농도)는 직접 측정 불가 → O2 몰분율의 sqrt 비례로 근사
#   - [N2]는 features.compute_n2_fraction 결과 사용
#   - 결과를 ppm/초 스케일로 정규화
# ============================================================
def zeldovich_nox_rate(
    exhaust_temp_c: float,
    o2_fraction: float,
    n2_fraction: float,
    consts: ZeldovichConstants = DEFAULT_ZELDOVICH,
) -> float:
    """NOx 생성률 [ppm/s] 근사.

    Args:
        exhaust_temp_c: 배기 온도 [°C]. IGCC.CC.G1.TTXM 실측 기반.
        o2_fraction:    배기 O2 몰분율 (0~1).
        n2_fraction:    배기 N2 몰분율 (0~1).
        consts:         Arrhenius 상수.

    Returns:
        생성률 [ppm/s]. consts.max_nox_rate_ppm_per_s 상한 클램프.
    """
    # Arrhenius는 절대온도(K) 기반 — °C → K 변환
    temp_k = exhaust_temp_c + 273.15
    k1 = arrhenius_rate_constant(temp_k, consts)

    # [O]를 O2 몰분율의 sqrt에 비례한다고 단순 가정
    # (정확한 dissociation 평형은 Cantera 필요)
    o_atom_proxy = math.sqrt(max(0.0, o2_fraction))

    # 정규화 스케일 — 가안. 추후 ML 회귀 결과와 캘리브레이션 필요 [조사 필요].
    SCALE_PPM = 1.0e-6

    rate = 2.0 * k1 * o_atom_proxy * n2_fraction * SCALE_PPM

    # 폭주 방지
    return min(rate, consts.max_nox_rate_ppm_per_s)


# ============================================================
# 3) Forward Euler 적분 step
# [가이드 단계 3 — ODE 적분기 / 수치 불안정성 방지 로직]
# ------------------------------------------------------------
# 단순한 1-step Euler. 추후 RK4 또는 scipy.integrate.solve_ivp로 교체 가능
# (가이드 §10 오픈 이슈: 적분기 최종 선택 [추후 결정]).
# ============================================================
def integrate_zeldovich_step(
    nox_current: float,
    exhaust_temp_c: float,
    o2_fraction: float,
    n2_fraction: float,
    dt: float,
    *,
    consts: ZeldovichConstants = DEFAULT_ZELDOVICH,
    nox_floor: float = 0.0,
    nox_ceiling: float = 1000.0,  # [ppm] [조사 필요] 물리적 상한
) -> float:
    """현재 NOx에서 dt만큼 Zeldovich ODE를 적분.

    Args:
        nox_current:    현재 NOx 농도 [ppm].
        exhaust_temp_c: 배기 온도 [°C]. IGCC.CC.G1.TTXM 실측 기반.
        o2_fraction:    배기 O2 몰분율.
        n2_fraction:  배기 N2 몰분율.
        dt:           적분 시간 [초].
        consts:       반응 상수.
        nox_floor:    수치 오차로 음수가 되지 않도록 floor.
        nox_ceiling:  비물리적 폭주 방지 상한.

    Returns:
        다음 step의 NOx [ppm].

    Notes:
        - 계산 실패(NaN/Inf) 시 입력값 그대로 반환 (가이드 단계 3 fallback 기준).
    """
    try:
        rate = zeldovich_nox_rate(exhaust_temp_c, o2_fraction, n2_fraction, consts)
        next_nox = nox_current + rate * dt

        # NaN/Inf 가드
        if not math.isfinite(next_nox):
            return nox_current

        return max(nox_floor, min(nox_ceiling, next_nox))
    except (ValueError, OverflowError):
        # 가이드 단계 3 — "비정상 값 fallback 처리": 이전 값 유지
        return nox_current


# ============================================================
# 4) 정상상태 NOx 추정 (참고용)
# [가이드 단계 3 — 정상상태 검증 / 단계 4 ML 회귀와의 대조용]
# ------------------------------------------------------------
# Zeldovich가 무한 시간 적분되었을 때 수렴할 NOx 값의 근사.
# ML 회귀 결과 검증 시 동일 입력을 넣었을 때 정성적 일치 여부 확인용.
# ============================================================
def estimate_steady_nox(
    exhaust_temp_c: float,
    o2_fraction: float,
    n2_fraction: float,
    residence_time_s: float = 30.0,
    consts: ZeldovichConstants = DEFAULT_ZELDOVICH,
) -> float:
    """체류 시간만큼 Zeldovich rate로 적분한 정상상태 근사값.

    실제 정상상태는 평형 상수까지 풀어야 하지만, 프로토타입에서는
    "rate × residence_time"으로 충분히 동작 방향성을 확인 가능.
    """
    rate = zeldovich_nox_rate(exhaust_temp_c, o2_fraction, n2_fraction, consts)
    return max(0.0, rate * residence_time_s)
