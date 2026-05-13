import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from digital_twin.preprocess import RAW_FEATURES
from digital_twin.forecaster.preprocess import NOX_TARGET_COL


def _make_recent_df(n_rows: int = 1200) -> pd.DataFrame:
    """RAW_FEATURES + TTXM + NOx + DWATT + O2 컬럼을 가진 합성 recent_df."""
    from digital_twin.preprocess import RAW_FEATURES as _DT_RAW

    rng = np.random.default_rng(123)
    # forecaster의 RAW_FEATURES는 AIT_H1_902 포함, _DT_RAW는 제외
    cols = list(set(RAW_FEATURES + _DT_RAW))
    data = {col: rng.normal(100.0, 5.0, n_rows) for col in cols}
    data["IGCC.CC.G1.TTXM"] = rng.normal(540.0, 5.0, n_rows)
    data[NOX_TARGET_COL] = rng.normal(29.0, 0.2, n_rows)
    data["IGCC.CC.G1.DWATT"] = rng.normal(155.0, 5.0, n_rows)
    data["IGCC.DeNOX.AIT_H1_902"] = rng.normal(15.0, 0.5, n_rows)
    return pd.DataFrame(data)


def _train_dummy_model(tmp_path: Path):
    from digital_twin.forecaster.tests.test_preprocess import _make_synthetic_csv
    from digital_twin.forecaster.train import train_forecaster

    csv = tmp_path / "data.csv"
    _make_synthetic_csv(csv, n_seconds=2400)
    train_forecaster(
        csv_path=csv, output_dir=tmp_path,
        val_ratio=0.2, n_estimators=10, subsample_sec=5,
    )
    return (
        tmp_path / "forecaster_lgb_model.pkl",
        tmp_path / "forecaster_metadata.json",
    )


def test_predict_returns_float_with_sufficient_history(tmp_path: Path):
    from digital_twin.forecaster.predict import load_model, predict

    model_path, meta_path = _train_dummy_model(tmp_path)
    loaded = load_model(model_path=model_path, metadata_path=meta_path)
    recent_df = _make_recent_df(1200)
    result = predict(loaded, recent_df=recent_df)
    assert isinstance(result, float)
    assert np.isfinite(result)


def test_predict_raises_when_ttxm_missing(tmp_path: Path):
    from digital_twin.forecaster.predict import load_model, predict

    model_path, meta_path = _train_dummy_model(tmp_path)
    loaded = load_model(model_path=model_path, metadata_path=meta_path)
    recent_df = _make_recent_df(1200).drop(columns=["IGCC.CC.G1.TTXM"])
    with pytest.raises(ValueError, match="TTXM"):
        predict(loaded, recent_df=recent_df)


def test_predict_raises_when_nox_missing(tmp_path: Path):
    from digital_twin.forecaster.predict import load_model, predict

    model_path, meta_path = _train_dummy_model(tmp_path)
    loaded = load_model(model_path=model_path, metadata_path=meta_path)
    recent_df = _make_recent_df(1200).drop(columns=[NOX_TARGET_COL])
    with pytest.raises(ValueError, match="NOx"):
        predict(loaded, recent_df=recent_df)


def test_predict_warns_on_short_history(tmp_path: Path):
    from digital_twin.forecaster.predict import load_model, predict

    model_path, meta_path = _train_dummy_model(tmp_path)
    loaded = load_model(model_path=model_path, metadata_path=meta_path)
    short_df = _make_recent_df(30)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = predict(loaded, recent_df=short_df)
    assert isinstance(result, float)
    assert any("warm-up" in str(item.message).lower() or
               "유효" in str(item.message) for item in w)
