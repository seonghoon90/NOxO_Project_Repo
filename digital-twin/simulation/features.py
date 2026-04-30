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


# ============================================================
# 기준 운전점 — Stub Predictor와 동일 값 사용
# [가이드 단계 0 — 변수별 기본 step / 운영 한계 기준값]
# 추후 실측 데이터 통계로 교체 [DB 협의 필요]
# ============================================================
REF_SYNGAS_FLOW = 1500.0   # 합성가스 유량 기준점
REF_N2_OFFSET = 200.0      # 희석질소 오프셋 기준점
REF_IGV_OPENING = 75.0     # IGV 개도 기준점(%)


# ============================================================
# 1) 공기비 λ 계산
# [가이드 단계 2 — compute_lambda]
# ------------------------------------------------------------
# 의미:
#   λ = (실제 공급 공기) / (이론 화학량론적 공기)
#   λ > 1 : 공기 과잉 (lean), NOx 증가 경향
#   λ < 1 : 연료 과잉 (rich), CO 증가 경향
#
# 정확한 계산은 합성가스 조성(H2/CO/CH4 비율)이 필요하지만
# 프로토타입에서는 IGV 개도(공기 유량 비례) / 합성가스 유량의
# 비율로 근사한다. n2_offset은 미세 보정 항으로 처리.
# ============================================================
def compute_lambda(
    syngas_flow: float,
    n2_offset: float,
    igv_opening: float,
    *,
    base_lambda: float = 1.10,
    n2_correction: float = 0.0005,
) -> float:
    """공기비 λ 근사 계산.

    Args:
        syngas_flow: 합성가스 유량.
        n2_offset:   희석질소 오프셋.
        igv_opening: IGV 개도(%) — 공기 유량 비례 변수로 사용.
        base_lambda: 기준 운전점에서의 λ. [DB 협의 필요] 실측 평균값으로 교체 예정.
        n2_correction: N2 1단위 증가당 λ 보정 계수.

    Returns:
        λ (무차원). 0.5 미만으로 떨어지지 않도록 클램프.
    """
    # 0으로 나눗셈 방지
    igv_ratio = max(igv_opening, 1.0) / REF_IGV_OPENING
    fuel_ratio = max(syngas_flow, 1.0) / REF_SYNGAS_FLOW

    # 공기 / 연료 비율로 λ 변동을 표현
    lambda_ = base_lambda * (igv_ratio / fuel_ratio)

    # N2 추가 → 약간의 lean 보정 (질량 추가 효과)
    lambda_ += (n2_offset - REF_N2_OFFSET) * n2_correction

    # 비물리적 음수/0 방지
    return max(0.5, lambda_)


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
    base_co: float = 12.0,
    sensitivity: float = 80.0,
) -> float:
    """CO 농도 근사 계산.

    Args:
        lambda_:     공기비.
        base_co:     λ=1에서의 CO 베이스라인. [조사 필요] 실측 도출.
        sensitivity: (λ-1)^2 항의 가중치. [조사 필요].

    Returns:
        CO 농도(ppm 가안). 0 미만 클램프.
    """
    return max(0.0, base_co + sensitivity * (lambda_ - 1.0) ** 2)


# ============================================================
# 3) 발전 효율 계산
# [가이드 단계 2 — compute_efficiency]
# ------------------------------------------------------------
# 정확한 효율은 입력 열량(LHV × 합성가스 유량) 대비 발전량이지만,
# 프로토타입에서는 운전점 근처 0.85~0.92 영역의 단순 근사식을 쓴다.
# ============================================================
def compute_efficiency(
    syngas_flow: float,
    flame_temp: float,
    *,
    base_efficiency: float = 0.89,
    temp_sensitivity: float = 0.0001,
) -> float:
    """발전 효율 근사.

    Args:
        syngas_flow:      합성가스 유량.
        flame_temp:       현재 화염 온도(K).
        base_efficiency:  기준 효율. [추후 결정]
        temp_sensitivity: 온도 1K 변동당 효율 변동. [조사 필요]

    Returns:
        무차원 효율. [0.0, 1.0] 클램프.
    """
    # 화염 온도가 기준점(1450K)보다 높으면 효율 약간 증가 — 카르노 사이클 직관
    # 너무 높아지면 NOx 패널티가 따로 잡으므로 본 함수에서는 단순 선형 가정
    eta = base_efficiency + (flame_temp - 1450.0) * temp_sensitivity

    # 합성가스 유량이 기준점에서 멀어지면 효율 약간 감소 (off-design 패널티)
    fuel_deviation = abs(syngas_flow - REF_SYNGAS_FLOW) / REF_SYNGAS_FLOW
    eta -= fuel_deviation * 0.02

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
    ref_air_flow: float = 4500.0,  # IGV 75%일 때 가안 공기유량 [kg/h]
) -> float:
    """IGV 개도 → 추정 공기 유량.

    선형 비례 가정 (실제는 비선형이지만 프로토타입 한정 단순화).
    """
    return ref_air_flow * (igv_opening / REF_IGV_OPENING)


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
    o2_in_air: float = 0.21,
) -> float:
    """λ로부터 배기 중 O2 몰분율 근사.

    λ=1이면 O2 거의 0, λ>1이면 잉여 산소 비례 증가.
    """
    if lambda_ <= 1.0:
        return 0.0
    # 단순 가정: 잉여 공기의 O2가 그대로 잔존
    excess_air_ratio = (lambda_ - 1.0) / lambda_
    return o2_in_air * excess_air_ratio


def compute_n2_fraction(
    lambda_: float,
    n2_offset: float,
    *,
    n2_in_air: float = 0.79,
) -> float:
    """배기 중 N2 몰분율 근사.

    공기 중 N2 + 희석 N2 주입분을 합산. Zeldovich의 N2 분압 입력으로 사용.
    """
    # 희석 N2는 base 기준 대비 증가분만큼 N2 몰분율을 증가시킨다고 가정
    delta_n2 = max(0.0, (n2_offset - REF_N2_OFFSET) / 1000.0)
    return min(1.0, n2_in_air + delta_n2)
