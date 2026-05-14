"""파생 피처 계산 모듈.

[가이드 §5 — 단계 2 "도메인 계산식과 파생 피처 정의"]
- ML 학습 시점과 시뮬 런타임이 동일한 함수를 재사용해야
  학습/추론 간 피처 불일치(skew)가 발생하지 않는다.
- 따라서 본 모듈은 학습 스크립트(`analysis/Engineering/scripts/`)에서도
  동일하게 import 해서 쓰도록 설계한다.

본 파일에 포함되는 함수의 책임:
1) compute_lambda      : 공기비 λ — Zeldovich 입력으로 직결
2) compute_co          : CO 농도 — λ=1 근처 최저, 멀어질수록 증가
3) compute_efficiency  : 발전 효율 근사
4) compute_air_flow    : IGV 개도 → 공기 유량 환산 (보조)

수치 상수는 모두 함수 인자로 노출해 학습/시뮬 양쪽에서 같은 값을 쓰도록 강제한다.
실제 값은 [DB 협의 필요] / [조사 필요] 마커 영역으로, 프로토타입 단계에서는 가안값을 사용한다.
"""

from __future__ import annotations

import math

from .config import DEFAULT_CONFIG, FeatureConfig, OperatingPoint

_OP = DEFAULT_CONFIG.operating_point
_FC = DEFAULT_CONFIG.features


# ============================================================
# 1) 공기비 λ 계산
# [가이드 단계 2 — compute_lambda]
# ------------------------------------------------------------
# 의미:
#   λ = (실제 공급 공기) / (이론 화학량론적 공기)
#   λ > 1 : 공기 과잉 (lean), NOx 증가 경향
#   λ < 1 : 연료 과잉 (rich), CO 증가 경향
#
# 우선순위:
#   1) 배기 O2 측정값(AIT_H1_902)이 있으면 표준 역산식
#      λ = 20.9 / (20.9 - O2_dry_pct)
#      산업 표준 (EPA 40 CFR Part 60). 가스터빈 정상 λ=2~4가 자연스럽게 산출.
#   2) O2 측정이 없으면 IGV/syngas 비율 근사식으로 폴백
#      (합성가스 조성/공기 유량 직접 측정이 없을 때의 차선).
# ============================================================
_O2_IN_AIR_PCT = 20.9  # 대기 중 O2 부피% (건조 기준)


def compute_lambda(
    syngas_flow: float,
    n2_offset: float,
    igv_opening: float,
    *,
    o2_dry_pct: float | None = None,
    op: OperatingPoint = _OP,
    fc: FeatureConfig = _FC,
) -> float:
    """공기비 λ 계산. O2 측정값이 있으면 역산식, 없으면 근사식 폴백.

    Args:
        syngas_flow: 합성가스 유량 (폴백 경로 입력).
        n2_offset:   희석질소 오프셋 (폴백 경로 입력).
        igv_opening: IGV 개도(%) — 폴백 경로의 공기 유량 비례 변수.
        o2_dry_pct: 배기 건조 O2 농도 [%]. None/비현실값이면 폴백.
        op: 기준 운전점 설정 (폴백 경로).
        fc: 피처 계산 상수 (폴백 경로).

    Returns:
        λ (무차원). lambda_min 미만으로 떨어지지 않도록 클램프.
    """
    if o2_dry_pct is not None and math.isfinite(o2_dry_pct):
        # O2가 대기 농도(20.9%) 이상이면 측정 이상 — 폴백으로 전환
        if 0.0 <= o2_dry_pct < _O2_IN_AIR_PCT:
            denom = max(_O2_IN_AIR_PCT - o2_dry_pct, 0.5)
            lambda_ = _O2_IN_AIR_PCT / denom
            return max(DEFAULT_CONFIG.thresholds.lambda_min, lambda_)

    igv_ratio = max(igv_opening, 1.0) / op.igv_opening
    fuel_ratio = max(syngas_flow, 1.0) / op.syngas_flow

    lambda_ = fc.base_lambda * (igv_ratio / fuel_ratio)
    lambda_ += (n2_offset - op.n2_offset) * fc.n2_correction

    return max(DEFAULT_CONFIG.thresholds.lambda_min, lambda_)


# ============================================================
# 2) CO 농도 계산
# [가이드 단계 2 — compute_co_proxy]
# ------------------------------------------------------------
# 의미:
#   CO는 λ=1 근처에서 최저, λ가 1에서 멀어질수록 증가하는
#   U자형 거동을 보인다. 프로토타입에서는 (λ-1)^2 근사로 표현.
#   실측 데이터 확보 후 ML 회귀로 교체 예정.
# ============================================================
def compute_co(
    lambda_: float,
    *,
    fc: FeatureConfig = _FC,
) -> float:
    """CO 농도 근사 계산.

    Args:
        lambda_: 공기비.
        fc: 피처 계산 상수.

    Returns:
        CO 농도(ppm 가안). 0 미만 클램프.
    """
    return max(0.0, fc.base_co + fc.co_sensitivity * (lambda_ - 1.0) ** 2)


# ============================================================
# 3) 발전 효율 계산
# [가이드 단계 2 — compute_efficiency]
# ------------------------------------------------------------
# 정확한 효율은 입력 열량(LHV × 합성가스 유량) 대비 발전량이지만,
# 프로토타입에서는 운전점 근처 0.85~0.92 영역의 단순 근사식을 쓴다.
# ============================================================
def compute_efficiency(
    syngas_flow: float,
    exhaust_temp: float,
    *,
    op: OperatingPoint = _OP,
    fc: FeatureConfig = _FC,
) -> float:
    """발전 효율 근사.

    Args:
        syngas_flow:  합성가스 유량.
        exhaust_temp: 현재 배기 온도(°C). IGCC.CC.G1.TTXM 실측 기반.
        op: 기준 운전점 설정.
        fc: 피처 계산 상수.

    Returns:
        무차원 효율. [0.0, 1.0] 클램프.
    """
    eta = fc.base_efficiency + (exhaust_temp - op.exhaust_temp) * fc.temp_sensitivity

    fuel_deviation = abs(syngas_flow - op.syngas_flow) / op.syngas_flow
    eta -= fuel_deviation * fc.off_design_penalty

    return max(0.0, min(1.0, eta))


# ============================================================
# 3-2) 열역학적 발전 효율 계산 (실측 LHV 기반)
# [ASME PTC 22 표준: η = 전기출력 / 입력열량]
# ------------------------------------------------------------
# 의미:
#   η = power [MJ/s] / Q_in [MJ/s]
#   Q_in = syngas_flow [kg/s] × LHV_mass [MJ/kg]
#   LHV_mass [MJ/kg] = LHV_vol [kJ/Nm³] × 1e-3 / ρ_stp [kg/Nm³]
#
# ρ_stp는 LHV가 Nm³(0°C, 1 atm) 기준이므로 표준상태 밀도를 사용한다
#   ρ_stp = (P_0 × M) / (R × T_0)  ≈ 0.955 kg/Nm³ (M=21.4 g/mol)
# 운전 압력/온도(FPSG/FTSG)는 입력 열량 계산에 들어가지 않는다.
#
# 검증: 학습 CSV(86,401행, DWATT>50MW) 적용 시 mean=0.397, p5~p95=0.388~0.406
# GE 7F 단순 사이클 LHV 효율(~0.385) 도메인 범위 정합.
#
# 우선순위:
#   1) LHV 측정값 유효 → 실측 기반 계산
#   2) LHV 결측 → None 반환. 호출부가 폴백 처리.
# ============================================================
_R_GAS = 8.314      # 기체상수 [J/(mol·K)]
_STP_P_PA = 101325  # 표준상태 압력 [Pa]
_STP_T_K = 273.15   # 표준상태 온도 [K]


def _stp_density(molar_mass_g_per_mol: float) -> float:
    """표준상태(0°C, 1 atm) 이상기체 밀도 [kg/Nm³]."""
    return (_STP_P_PA * molar_mass_g_per_mol * 1e-3) / (_R_GAS * _STP_T_K)


def compute_efficiency_from_lhv(
    power_mw: float,
    syngas_flow: float,
    *,
    lhv_kj_per_nm3: float | None,
    molar_mass_g_per_mol: float,
) -> float | None:
    """실측 LHV 기반 발전 효율 (열역학 표준식).

    Args:
        power_mw: 발전기 출력 [MW = MJ/s]. Kafka DWATT.
        syngas_flow: 합성가스 질량유량 [kg/s]. Kafka ca_fqsg_cl.
        lhv_kj_per_nm3: 합성가스 부피 LHV [kJ/Nm³]. Kafka LHVSYNDW_SCF.
        molar_mass_g_per_mol: 합성가스 평균 분자량 [g/mol]. config 상수.

    Returns:
        효율 [무차원, 0.0~1.0 클램프]. 측정값 결측·비현실값일 때 None.
    """
    if lhv_kj_per_nm3 is None:
        return None
    if not (
        math.isfinite(lhv_kj_per_nm3)
        and math.isfinite(power_mw)
        and math.isfinite(syngas_flow)
    ):
        return None
    if lhv_kj_per_nm3 <= 0.0 or syngas_flow <= 0.0:
        return None

    rho_stp = _stp_density(molar_mass_g_per_mol)
    if rho_stp <= 0.0:
        return None

    # LHV 단위 환산: kJ/Nm³ → MJ/kg
    lhv_mj_per_kg = (lhv_kj_per_nm3 * 1e-3) / rho_stp

    input_heat_mj_per_s = syngas_flow * lhv_mj_per_kg
    if input_heat_mj_per_s <= 0.0:
        return None

    eta = power_mw / input_heat_mj_per_s
    return max(0.0, min(1.0, eta))


# ============================================================
# 4) 공기 유량 환산 (보조)
# ------------------------------------------------------------
# Zeldovich ODE 입력으로 O2/N2 분압이 필요한데,
# 현재 IGV 개도만 가지고 있으므로 단순 환산식을 둔다.
# 추후 실제 공기 유량 센서가 매핑되면 본 함수를 우회한다 [DB 협의 필요].
# ============================================================
def compute_air_flow(
    igv_opening: float,
    *,
    op: OperatingPoint = _OP,
) -> float:
    """IGV 개도 → 추정 공기 유량.

    선형 비례 가정 (실제는 비선형이지만 프로토타입 한정 단순화).
    """
    return op.air_flow * (igv_opening / op.igv_opening)


# ============================================================
# 5) O2 / N2 분압 추정 (Zeldovich 입력)
# [가이드 단계 3 보조 — Zeldovich ODE에 넣을 농도 변수]
# ------------------------------------------------------------
# 정확히는 연소 후 가스 조성을 풀어야 하지만, 프로토타입에서는
# λ로부터 산화 후 잔존 O2 비율을 근사한다.
# ============================================================
def compute_o2_fraction(
    lambda_: float,
    *,
    fc: FeatureConfig = _FC,
) -> float:
    """λ로부터 배기 중 O2 몰분율 근사.

    λ=1이면 O2 거의 0, λ>1이면 잉여 산소 비례 증가.
    """
    if lambda_ <= 1.0:
        return 0.0
    excess_air_ratio = (lambda_ - 1.0) / lambda_
    return fc.o2_in_air * excess_air_ratio


def compute_n2_fraction(
    lambda_: float,
    n2_offset: float,
    *,
    op: OperatingPoint = _OP,
    fc: FeatureConfig = _FC,
) -> float:
    """배기 중 N2 몰분율 근사.

    공기 중 N2 + 희석 N2 주입분을 합산. Zeldovich의 N2 분압 입력으로 사용.
    """
    delta_n2 = max(0.0, (n2_offset - op.n2_offset) / fc.n2_scale)
    return min(1.0, fc.n2_in_air + delta_n2)
