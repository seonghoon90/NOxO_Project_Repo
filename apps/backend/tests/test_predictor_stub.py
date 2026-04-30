"""Stub Predictor의 단조 거동(시그니처 도메인 직관) 검증.

진짜 ML 모델이 들어오기 전 프론트가 의존할 수 있는 응답 특성을 보장.
"""

from app.adapters.predictor import StubPredictor
from app.domain.tags import ControlVars


def test_higher_syngas_increases_flame_temp():
    p = StubPredictor()
    base = p.predict(ControlVars(syngas_flow=1500, n2_offset=200, igv_opening=75))
    high = p.predict(ControlVars(syngas_flow=1800, n2_offset=200, igv_opening=75))
    assert high.flame_temp > base.flame_temp


def test_more_n2_lowers_flame_temp():
    p = StubPredictor()
    base = p.predict(ControlVars(syngas_flow=1500, n2_offset=200, igv_opening=75))
    diluted = p.predict(ControlVars(syngas_flow=1500, n2_offset=400, igv_opening=75))
    assert diluted.flame_temp < base.flame_temp


def test_higher_igv_raises_lambda():
    p = StubPredictor()
    low = p.predict(ControlVars(syngas_flow=1500, n2_offset=200, igv_opening=60))
    high = p.predict(ControlVars(syngas_flow=1500, n2_offset=200, igv_opening=95))
    assert high.lambda_ > low.lambda_


def test_higher_temp_increases_nox():
    p = StubPredictor()
    cold = p.predict(ControlVars(syngas_flow=1300, n2_offset=300, igv_opening=70))
    hot = p.predict(ControlVars(syngas_flow=1900, n2_offset=100, igv_opening=85))
    assert hot.nox > cold.nox


def test_higher_load_increases_power():
    p = StubPredictor()
    base = p.predict(ControlVars(syngas_flow=1500, n2_offset=200, igv_opening=75))
    high = p.predict(ControlVars(syngas_flow=1700, n2_offset=200, igv_opening=90))
    assert high.power > base.power


def test_more_n2_lowers_power():
    p = StubPredictor()
    base = p.predict(ControlVars(syngas_flow=1500, n2_offset=200, igv_opening=75))
    diluted = p.predict(ControlVars(syngas_flow=1500, n2_offset=400, igv_opening=75))
    assert diluted.power < base.power
