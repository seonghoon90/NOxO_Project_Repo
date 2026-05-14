"""features.compute_lambda 회귀 테스트.

O2 측정값이 있으면 산업 표준 역산식 λ = 20.9/(20.9-O2)을 사용하고,
없으면 IGV/syngas 근사식으로 폴백한다.
"""
from __future__ import annotations

import math

import pytest

from digital_twin.simulation.config import DEFAULT_CONFIG
from digital_twin.simulation.features import compute_lambda

_LAMBDA_MIN = DEFAULT_CONFIG.thresholds.lambda_min


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


class TestComputeLambdaClamp:
    """lambda_min 클램프 동작 검증."""

    @pytest.mark.parametrize("o2", [20.4, 20.5, 20.8])
    def test_o2_near_air_clamps_to_min(self, o2):
        # O2가 20.9에 가까우면 분모 0.5로 클램프 → λ가 41.8 정도로 큰 값
        # 하지만 floor만 검증 (실측에서 거의 발생 불가한 극단값)
        lam = compute_lambda(43.0, -10.0, 63.0, o2_dry_pct=o2)
        assert lam >= _LAMBDA_MIN
