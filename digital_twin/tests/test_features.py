"""features.compute_lambda 회귀 테스트.

O2 측정값이 있으면 산업 표준 역산식 λ = 20.9/(20.9-O2)을 사용하고,
없으면 IGV/syngas 근사식으로 폴백한다.
"""
from __future__ import annotations

import math

import pytest

from digital_twin.simulation.config import DEFAULT_CONFIG
from digital_twin.simulation.features import (
    compute_efficiency_from_lhv,
    compute_lambda,
)

_LAMBDA_MIN = DEFAULT_CONFIG.thresholds.lambda_min
_M_SYNGAS = DEFAULT_CONFIG.features.syngas_molar_mass


class TestComputeLambdaWithO2:
    """O2 측정값이 주어진 경우 — 역산식 경로."""

    def test_o2_15pct_returns_lambda_near_3_5(self):
        # 가스터빈 정상 운전 — O2 15% → λ ≈ 3.54
        lam = compute_lambda(syngas_flow=43.0, n2_offset=-10.0, igv_opening=63.0, o2_dry_pct=15.0)
        assert math.isclose(lam, 20.9 / 5.9, rel_tol=1e-6)
        assert 3.4 < lam < 3.6

    def test_o2_10pct_returns_lambda_near_2(self):
        # 학습 데이터 mean(O2=10.07%) → λ ≈ 1.93
        lam = compute_lambda(syngas_flow=43.0, n2_offset=-10.0, igv_opening=63.0, o2_dry_pct=10.0)
        assert math.isclose(lam, 20.9 / 10.9, rel_tol=1e-6)
        assert 1.9 < lam < 2.0

    def test_lambda_in_normal_gt_operating_range(self):
        # 가스터빈 정상 운전 O2 13~15% → λ가 2~4 (도메인 임계)
        for o2 in (13.0, 14.0, 15.0):
            lam = compute_lambda(43.0, -10.0, 63.0, o2_dry_pct=o2)
            assert 2.0 <= lam <= 4.0, f"o2={o2} → λ={lam} out of [2,4]"

    def test_o2_inputs_ignore_fallback_inputs(self):
        # O2가 유효하면 syngas/igv 인자가 극단값이어도 결과는 O2로만 결정됨
        lam_a = compute_lambda(syngas_flow=43.0, n2_offset=-10.0, igv_opening=63.0, o2_dry_pct=15.0)
        lam_b = compute_lambda(syngas_flow=9999.0, n2_offset=999.0, igv_opening=1.0, o2_dry_pct=15.0)
        assert lam_a == lam_b

    def test_o2_at_air_concentration_falls_back(self):
        # O2 ≥ 20.9%면 측정 이상 (분모 0) → 폴백 경로로 전환
        lam = compute_lambda(syngas_flow=43.0, n2_offset=-10.0, igv_opening=63.0, o2_dry_pct=20.9)
        # 폴백 경로 결과와 동일해야 함
        lam_fallback = compute_lambda(43.0, -10.0, 63.0, o2_dry_pct=None)
        assert lam == lam_fallback


class TestComputeLambdaFallback:
    """O2가 None/NaN/음수일 때 — 근사식 폴백 경로."""

    def test_none_uses_fallback(self):
        lam = compute_lambda(syngas_flow=43.0, n2_offset=-10.0, igv_opening=63.0, o2_dry_pct=None)
        # 폴백 경로는 OperatingPoint 가안값과의 비율에 의존 — 값은 클램프만 검증
        assert lam >= _LAMBDA_MIN

    def test_nan_uses_fallback(self):
        lam_nan = compute_lambda(43.0, -10.0, 63.0, o2_dry_pct=float("nan"))
        lam_none = compute_lambda(43.0, -10.0, 63.0, o2_dry_pct=None)
        assert lam_nan == lam_none

    def test_negative_o2_uses_fallback(self):
        # 음수 O2는 측정 이상 → 폴백
        lam_neg = compute_lambda(43.0, -10.0, 63.0, o2_dry_pct=-1.0)
        lam_none = compute_lambda(43.0, -10.0, 63.0, o2_dry_pct=None)
        assert lam_neg == lam_none

    def test_fallback_default_kwarg_backward_compat(self):
        # o2_dry_pct 인자 생략 — 기존 시그니처 호환 유지
        lam = compute_lambda(syngas_flow=43.0, n2_offset=-10.0, igv_opening=63.0)
        assert lam >= _LAMBDA_MIN


class TestComputeLambdaFallbackOperatingPointAligned:
    """OperatingPoint 학습 분포 정합 회귀.

    가안 OperatingPoint(syngas_flow=1500 등)와 학습 평균(43)의 35배 괴리로
    폴백 λ가 32까지 폭주했던 버그 방지. 새 OperatingPoint(median 기반) +
    base_lambda=1.93 정합 후, 학습 mean 입력 시 폴백 λ가 정상 범위(1.5~2.5).
    """

    def test_fallback_at_training_mean_yields_normal_lambda(self):
        # 학습 데이터 mean (DWATT>50MW 구간)
        lam = compute_lambda(
            syngas_flow=43.0,   # ca_fqsg_cl median
            n2_offset=-10.0,    # NQKR3_MONITOR median
            igv_opening=63.0,   # csgv median
            o2_dry_pct=None,    # 폴백 강제
        )
        # base_lambda=1.93 + 정합 비율(=1) → λ≈1.93 부근
        assert 1.5 < lam < 2.5, f"폴백 λ={lam} 학습 평균에서 비정상"

    def test_fallback_no_longer_explodes(self):
        # 회귀: 가안 OperatingPoint(1500) 시절 λ=32 발생 — 절대 재현 안 돼야 함
        lam = compute_lambda(43.0, -10.0, 63.0, o2_dry_pct=None)
        assert lam < 10.0, f"폴백 λ={lam} 가안값 회귀 발생"


class TestComputeLambdaClamp:
    """lambda_min 클램프 동작 검증."""

    @pytest.mark.parametrize("o2", [20.4, 20.5, 20.8])
    def test_o2_near_air_clamps_to_min(self, o2):
        # O2가 20.9에 가까우면 분모 0.5로 클램프 → λ가 41.8 정도로 큰 값
        # 하지만 floor만 검증 (실측에서 거의 발생 불가한 극단값)
        lam = compute_lambda(43.0, -10.0, 63.0, o2_dry_pct=o2)
        assert lam >= _LAMBDA_MIN


class TestComputeEfficiencyFromLHV:
    """LHV 실측 기반 발전 효율 회귀 테스트.

    학습 CSV 평균 입력(DWATT=164, ca_fqsg_cl=43, LHVSYNDW_SCF=9170)에서
    η ≈ 0.397 — GE 7F 단순 사이클 LHV 효율 도메인 표준값 정합.
    """

    def test_nominal_inputs_match_domain_efficiency(self):
        eta = compute_efficiency_from_lhv(
            power_mw=164.26,
            syngas_flow=43.14,
            lhv_kj_per_nm3=9170.23,
            molar_mass_g_per_mol=_M_SYNGAS,
        )
        # 학습 데이터 mean 0.3968. 분자량 가정 ±10% 안에서 검증
        assert eta is not None
        assert 0.35 < eta < 0.45, f"η={eta} out of GE 7F domain range"

    def test_in_operating_range_for_typical_lhv(self):
        # LHV가 plant 정상 변동 범위(9100~9220)일 때 효율이 0.30~0.45 안
        for lhv in (9100, 9150, 9200, 9220):
            eta = compute_efficiency_from_lhv(
                power_mw=164.0,
                syngas_flow=43.0,
                lhv_kj_per_nm3=lhv,
                molar_mass_g_per_mol=_M_SYNGAS,
            )
            assert eta is not None
            assert 0.30 <= eta <= 0.45, f"lhv={lhv} → η={eta} out of [0.30,0.45]"

    def test_efficiency_clamped_to_unit_interval(self):
        # 비현실적 입력에서도 [0, 1] 안에 떨어짐
        eta = compute_efficiency_from_lhv(
            power_mw=1000.0,  # 비현실적으로 큰 출력
            syngas_flow=1.0,
            lhv_kj_per_nm3=9170.0,
            molar_mass_g_per_mol=_M_SYNGAS,
        )
        assert eta is not None
        assert 0.0 <= eta <= 1.0

    def test_lhv_none_returns_none(self):
        # LHV 결측 → None. 호출부가 폴백 처리.
        assert compute_efficiency_from_lhv(
            power_mw=164.0,
            syngas_flow=43.0,
            lhv_kj_per_nm3=None,
            molar_mass_g_per_mol=_M_SYNGAS,
        ) is None

    def test_lhv_nan_returns_none(self):
        assert compute_efficiency_from_lhv(
            power_mw=164.0,
            syngas_flow=43.0,
            lhv_kj_per_nm3=float("nan"),
            molar_mass_g_per_mol=_M_SYNGAS,
        ) is None

    def test_lhv_non_positive_returns_none(self):
        for lhv in (0.0, -1.0):
            assert compute_efficiency_from_lhv(
                power_mw=164.0,
                syngas_flow=43.0,
                lhv_kj_per_nm3=lhv,
                molar_mass_g_per_mol=_M_SYNGAS,
            ) is None

    def test_zero_syngas_flow_returns_none(self):
        # 트립·정지 상태에서 분모 0 방지
        assert compute_efficiency_from_lhv(
            power_mw=0.0,
            syngas_flow=0.0,
            lhv_kj_per_nm3=9170.0,
            molar_mass_g_per_mol=_M_SYNGAS,
        ) is None

    def test_efficiency_scales_inversely_with_lhv(self):
        # 같은 출력·유량에서 LHV가 커지면 효율은 작아짐 (입력 열량 증가)
        eta_low = compute_efficiency_from_lhv(
            power_mw=164.0, syngas_flow=43.0,
            lhv_kj_per_nm3=9000.0, molar_mass_g_per_mol=_M_SYNGAS,
        )
        eta_high = compute_efficiency_from_lhv(
            power_mw=164.0, syngas_flow=43.0,
            lhv_kj_per_nm3=9400.0, molar_mass_g_per_mol=_M_SYNGAS,
        )
        assert eta_low is not None and eta_high is not None
        assert eta_low > eta_high
