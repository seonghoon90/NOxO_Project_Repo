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

from .config import DEFAULT_CONFIG, ChemistryConfig, ThresholdConfig

_GAS_CONSTANT_R = 8.314   # 보편 기체 상수 [J/(mol·K)] — 물리상수이므로 config 미포함
_KELVIN_OFFSET = 273.15   # °C → K 변환 오프셋 — 물리상수이므로 config 미포함
_ZELDOVICH_FACTOR = 2.0   # d[NO]/dt 식의 반응 화학량론 계수 (물리 고정값)


# ============================================================
# 1) Arrhenius 속도상수 계산
# [가이드 단계 3 — Zeldovich 반응률 함수의 구성 요소]
# ============================================================
def arrhenius_rate_constant(
    temperature_k: float,
    cc: ChemistryConfig = DEFAULT_CONFIG.chemistry,
) -> float:
    """k(T) = A * exp(-Ea / (R*T))

    Args:
        temperature_k: 화염 온도 [K]. 양수여야 함.
        cc:            Zeldovich 반응 상수.

    Returns:
        반응 속도 상수. 단위는 입력 상수에 의존.

    Notes:
        - 1500K 부근에서 급격히 증가 (Thermal NOx의 특징)
        - 1300K 미만에서는 거의 0
    """
    if temperature_k <= 0:
        return 0.0
    exponent = -cc.activation_energy_Ea / (_GAS_CONSTANT_R * temperature_k)
    if exponent < -700.0:
        return 0.0
    return cc.pre_exponential_A * math.exp(exponent)


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
    cc: ChemistryConfig = DEFAULT_CONFIG.chemistry,
    tc: ThresholdConfig = DEFAULT_CONFIG.thresholds,
) -> float:
    """NOx 생성률 [ppm/s] 근사.

    Args:
        exhaust_temp_c: 배기 온도 [°C]. IGCC.CC.G1.TTXM 실측 기반.
        o2_fraction:    배기 O2 몰분율 (0~1).
        n2_fraction:    배기 N2 몰분율 (0~1).
        cc:             Zeldovich 반응 상수.
        tc:             임계치 설정.

    Returns:
        생성률 [ppm/s]. tc.nox_rate_max_ppm_per_s 상한 클램프.
    """
    temp_k = exhaust_temp_c + _KELVIN_OFFSET
    k1 = arrhenius_rate_constant(temp_k, cc)

    o_atom_proxy = math.sqrt(max(0.0, o2_fraction))

    rate = _ZELDOVICH_FACTOR * k1 * o_atom_proxy * n2_fraction * cc.scale_ppm

    return min(rate, tc.nox_rate_max_ppm_per_s)


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
    cc: ChemistryConfig = DEFAULT_CONFIG.chemistry,
    tc: ThresholdConfig = DEFAULT_CONFIG.thresholds,
) -> float:
    """현재 NOx에서 dt만큼 Zeldovich ODE를 적분.

    Args:
        nox_current:    현재 NOx 농도 [ppm].
        exhaust_temp_c: 배기 온도 [°C]. IGCC.CC.G1.TTXM 실측 기반.
        o2_fraction:    배기 O2 몰분율.
        n2_fraction:    배기 N2 몰분율.
        dt:             적분 시간 [초].
        cc:             반응 상수.
        tc:             임계치 설정.

    Returns:
        다음 step의 NOx [ppm].

    Notes:
        - 계산 실패(NaN/Inf) 시 입력값 그대로 반환 (가이드 단계 3 fallback 기준).
    """
    try:
        rate = zeldovich_nox_rate(exhaust_temp_c, o2_fraction, n2_fraction, cc, tc)
        next_nox = nox_current + rate * dt

        if not math.isfinite(next_nox):
            return nox_current

        return max(tc.nox_floor_ppm, min(tc.nox_ceiling_ppm, next_nox))
    except (ValueError, OverflowError):
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
    cc: ChemistryConfig = DEFAULT_CONFIG.chemistry,
    tc: ThresholdConfig = DEFAULT_CONFIG.thresholds,
) -> float:
    """체류 시간만큼 Zeldovich rate로 적분한 정상상태 근사값.

    실제 정상상태는 평형 상수까지 풀어야 하지만, 프로토타입에서는
    "rate × residence_time"으로 충분히 동작 방향성을 확인 가능.
    """
    rate = zeldovich_nox_rate(exhaust_temp_c, o2_fraction, n2_fraction, cc, tc)
    return max(0.0, rate * residence_time_s)
