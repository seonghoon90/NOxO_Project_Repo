from pathlib import Path

import joblib
import numpy as np
import pytest

from app.adapters.forecaster.base import ForecastInput
from app.adapters.forecaster.ml import MLForecaster
from app.exceptions import PredictorUnavailableError


class _StubModel:
    """joblib.dump/load 가능한 결정적 stub. MagicMock은 pickle 불가."""

    def __init__(self, return_value: float) -> None:
        self.return_value = return_value
        self.last_features = None

    def predict(self, features_df):
        self.last_features = features_df
        return np.array([self.return_value])


def test_missing_model_raises_at_init(tmp_path: Path):
    missing = tmp_path / "no_such_model.pkl"
    with pytest.raises(PredictorUnavailableError):
        MLForecaster(model_path=str(missing))


def test_predict_returns_float(tmp_path: Path):
    """모델 로드 + predict 호출 후 float 반환."""
    model_path = tmp_path / "stub.pkl"
    joblib.dump(_StubModel(32.1), model_path)

    forecaster = MLForecaster(model_path=str(model_path))
    inputs = ForecastInput(features={
        "syngas_flow": 100.0, "igv_opening": 80.0, "n2_offset": 5.0,
        "n2_valve_1": 42.0, "syngas_srv": 60.0, "syngas_gcv_1": 55.0,
        "syngas_gcv_1a": 54.0, "syngas_gcv_2": 53.0, "ibh_valve": 30.0,
        "n2_flow": 25.0,
    })
    result = forecaster.predict(inputs)
    assert isinstance(result, float)
    assert result == 32.1


def test_name_is_ml(tmp_path: Path):
    model_path = tmp_path / "stub.pkl"
    joblib.dump(_StubModel(0.0), model_path)
    assert MLForecaster(model_path=str(model_path)).name == "ml"
