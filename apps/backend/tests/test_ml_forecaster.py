"""MLForecaster 어댑터 단위 테스트.

신규 시그니처: ForecastInput.recent_df (IGCC raw tag DataFrame) → float.
모델/메타데이터 파일 부재 시 PredictorUnavailableError raise.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from app.adapters.forecaster.base import ForecastInput
from app.adapters.forecaster.ml import MLForecaster
from app.exceptions import PredictorUnavailableError


class _StubModel:
    """joblib.dump/load 가능한 결정적 stub. digital_twin.forecaster.predict가
    내부에서 .predict(X)를 호출한다.
    """

    def __init__(self, return_value: float) -> None:
        self.return_value = return_value
        self.last_X = None

    def predict(self, X):
        self.last_X = X
        return np.array([self.return_value])


def _write_metadata(path: Path, npr_threshold: float = 0.0) -> None:
    path.write_text(json.dumps({"npr_hinge_threshold": npr_threshold}))


def test_missing_model_raises_at_init(tmp_path: Path):
    missing = tmp_path / "no_model.pkl"
    metap = tmp_path / "meta.json"
    _write_metadata(metap)
    with pytest.raises(PredictorUnavailableError):
        MLForecaster(model_path=str(missing), metadata_path=str(metap))


def test_missing_metadata_raises_at_init(tmp_path: Path):
    model_path = tmp_path / "stub.pkl"
    joblib.dump(_StubModel(0.0), model_path)
    missing_meta = tmp_path / "no_meta.json"
    with pytest.raises(PredictorUnavailableError):
        MLForecaster(model_path=str(model_path), metadata_path=str(missing_meta))


def test_predict_requires_recent_df(tmp_path: Path):
    model_path = tmp_path / "stub.pkl"
    metap = tmp_path / "meta.json"
    joblib.dump(_StubModel(0.0), model_path)
    _write_metadata(metap)
    forecaster = MLForecaster(model_path=str(model_path), metadata_path=str(metap))
    with pytest.raises(PredictorUnavailableError):
        forecaster.predict(ForecastInput(features={"any": 1.0}, recent_df=None))


def test_predict_returns_float(tmp_path: Path):
    """digital_twin.forecaster.predict 위임 경로 — 최소 컬럼만 채워 호출.

    실제 RAW_FEATURES 39개 + TTXM + NOx + DWATT를 0으로 채워 통과시킨다.
    피처 엔지니어링은 ffill 폴백 경로로 진행(warmup 부족 경고).
    """
    from digital_twin.forecaster.predict import (
        DWATT_COL,
        TTXM_COL,
    )
    from digital_twin.forecaster.preprocess import NOX_TARGET_COL, RAW_FEATURES

    model_path = tmp_path / "stub.pkl"
    metap = tmp_path / "meta.json"
    joblib.dump(_StubModel(29.5), model_path)
    _write_metadata(metap)
    forecaster = MLForecaster(model_path=str(model_path), metadata_path=str(metap))

    cols = set(RAW_FEATURES) | {TTXM_COL, NOX_TARGET_COL, DWATT_COL}
    recent = pd.DataFrame({c: [0.0] * 10 for c in cols})

    result = forecaster.predict(ForecastInput(recent_df=recent))
    assert isinstance(result, float)
    assert result == pytest.approx(29.5)


def test_name_is_ml(tmp_path: Path):
    model_path = tmp_path / "stub.pkl"
    metap = tmp_path / "meta.json"
    joblib.dump(_StubModel(0.0), model_path)
    _write_metadata(metap)
    assert MLForecaster(
        model_path=str(model_path), metadata_path=str(metap)
    ).name == "ml"
