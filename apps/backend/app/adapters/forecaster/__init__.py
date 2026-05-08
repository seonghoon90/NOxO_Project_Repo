from app.adapters.forecaster.base import (
    Forecaster,
    ForecastInput,
    ForecastOutput,
)
from app.adapters.forecaster.stub import StubForecaster

__all__ = ["Forecaster", "ForecastInput", "ForecastOutput", "StubForecaster"]
