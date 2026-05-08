"""StubForecaster의 단조 거동 검증.

5분 horizon 단발 NOx 예측 stub — 실제 시계열 ML 도입 전까지의 placeholder.
"""

from app.adapters.forecaster import ForecastInput, StubForecaster


def test_empty_features_returns_base():
    f = StubForecaster()
    nox = f.predict(ForecastInput(features={}))
    assert nox == StubForecaster.BASE_NOX


def test_higher_syngas_increases_nox_forecast():
    f = StubForecaster()
    base = f.predict(ForecastInput(features={"syngas_flow": 1500.0}))
    high = f.predict(ForecastInput(features={"syngas_flow": 1900.0}))
    assert high > base


def test_more_n2_offset_lowers_nox_forecast():
    f = StubForecaster()
    base = f.predict(ForecastInput(features={"n2_offset": 200.0}))
    diluted = f.predict(ForecastInput(features={"n2_offset": 400.0}))
    assert diluted < base


def test_higher_igv_increases_nox_forecast():
    f = StubForecaster()
    low = f.predict(ForecastInput(features={"igv_opening": 60.0}))
    high = f.predict(ForecastInput(features={"igv_opening": 95.0}))
    assert high > low
