"""StubSimulator의 단조 거동(시그니처 도메인 직관) 검증.

진짜 ML 모델이 들어오기 전 프론트가 의존할 수 있는 응답 특성을 보장.
기존 3변수(syngas/n2/igv) + 신규 7변수의 단조성을 모두 검증한다.
"""

from dataclasses import replace

from app.adapters.simulator import StubSimulator
from digital_twin.simulation import ControlVars


def _controls(syngas_flow: float = 1500.0, n2_offset: float = 200.0, igv_opening: float = 75.0) -> ControlVars:
    """기존 3변수만 변동시키는 헬퍼 — 신규 7변수는 운영 기준값 고정."""
    return ControlVars(
        syngas_flow=syngas_flow,
        igv_opening=igv_opening,
        n2_offset=n2_offset,
        n2_valve_1=50.0,
        syngas_srv=60.0,
        syngas_gcv_1=55.0,
        syngas_gcv_1a=55.0,
        syngas_gcv_2=55.0,
        ibh_valve=30.0,
        n2_flow=100.0,
    )


def test_higher_syngas_increases_exhaust_temp():
    s = StubSimulator()
    base = s.predict(_controls(syngas_flow=1500, n2_offset=200, igv_opening=75))
    high = s.predict(_controls(syngas_flow=1800, n2_offset=200, igv_opening=75))
    assert high.exhaust_temp > base.exhaust_temp


def test_more_n2_lowers_exhaust_temp():
    s = StubSimulator()
    base = s.predict(_controls(syngas_flow=1500, n2_offset=200, igv_opening=75))
    diluted = s.predict(_controls(syngas_flow=1500, n2_offset=400, igv_opening=75))
    assert diluted.exhaust_temp < base.exhaust_temp


def test_higher_igv_raises_lambda():
    s = StubSimulator()
    low = s.predict(_controls(syngas_flow=1500, n2_offset=200, igv_opening=60))
    high = s.predict(_controls(syngas_flow=1500, n2_offset=200, igv_opening=95))
    assert high.lambda_ > low.lambda_


def test_higher_temp_increases_nox():
    s = StubSimulator()
    cold = s.predict(_controls(syngas_flow=1300, n2_offset=300, igv_opening=70))
    hot = s.predict(_controls(syngas_flow=1900, n2_offset=100, igv_opening=85))
    assert hot.nox > cold.nox


def test_higher_load_increases_power():
    s = StubSimulator()
    base = s.predict(_controls(syngas_flow=1500, n2_offset=200, igv_opening=75))
    high = s.predict(_controls(syngas_flow=1700, n2_offset=200, igv_opening=90))
    assert high.power > base.power


def test_more_n2_lowers_power():
    s = StubSimulator()
    base = s.predict(_controls(syngas_flow=1500, n2_offset=200, igv_opening=75))
    diluted = s.predict(_controls(syngas_flow=1500, n2_offset=400, igv_opening=75))
    assert diluted.power < base.power


# ============================================================
# 신규 7변수 단조성 — P3
# ============================================================


def test_more_n2_valve_1_lowers_nox():
    s = StubSimulator()
    base = s.predict(_controls())
    diluted = s.predict(replace(_controls(), n2_valve_1=90.0))
    assert diluted.nox < base.nox


def test_more_n2_flow_lowers_nox():
    s = StubSimulator()
    base = s.predict(_controls())
    diluted = s.predict(replace(_controls(), n2_flow=400.0))
    assert diluted.nox < base.nox


def test_more_syngas_srv_increases_power():
    s = StubSimulator()
    base = s.predict(_controls())
    high = s.predict(replace(_controls(), syngas_srv=95.0))
    assert high.power > base.power


def test_more_syngas_gcv_1_increases_exhaust_temp():
    s = StubSimulator()
    base = s.predict(_controls())
    high = s.predict(replace(_controls(), syngas_gcv_1=90.0))
    assert high.exhaust_temp > base.exhaust_temp


def test_more_syngas_gcv_1a_increases_power():
    s = StubSimulator()
    base = s.predict(_controls())
    high = s.predict(replace(_controls(), syngas_gcv_1a=90.0))
    assert high.power > base.power


def test_more_syngas_gcv_2_increases_exhaust_temp():
    s = StubSimulator()
    base = s.predict(_controls())
    high = s.predict(replace(_controls(), syngas_gcv_2=90.0))
    assert high.exhaust_temp > base.exhaust_temp


def test_more_ibh_valve_lowers_efficiency():
    s = StubSimulator()
    base = s.predict(_controls())
    high = s.predict(replace(_controls(), ibh_valve=80.0))
    assert high.efficiency < base.efficiency
