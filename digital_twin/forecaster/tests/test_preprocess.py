from pathlib import Path

import numpy as np
import pandas as pd

from digital_twin.forecaster.preprocess import (
    FEATURES,
    FORECAST_HORIZON_SEC,
    NOX_LAG_FEATURES,
    NOX_TARGET_COL,
    TARGET_COL,
    add_nox_lag_features,
    make_forecast_target_1s,
)


def _make_synthetic_csv(path: Path, n_seconds: int = 600) -> None:
    from digital_twin.preprocess import RAW_FEATURES, TARGETS

    rng = np.random.default_rng(42)
    n = n_seconds
    data = {col: rng.normal(100.0, 5.0, n) for col in RAW_FEATURES}
    for col in TARGETS:
        data[col] = rng.normal(50.0, 2.0, n)
    # v2.7: 직접 O2 센서 컬럼 (forecaster가 별도로 load함)
    data["IGCC.DeNOX.AIT_H1_902"] = rng.normal(15.0, 0.5, n)

    df = pd.DataFrame(data)
    df.index.name = "timestamp"
    df.to_csv(path, encoding="utf-8-sig")

    raw = path.read_text(encoding="utf-8-sig").splitlines()
    header = raw[0]
    body = raw[1:]
    n_cols = header.count(",") + 1
    dummy = [",".join(["meta"] * n_cols)] * 4
    path.write_text(
        "\n".join([header] + dummy + body) + "\n",
        encoding="utf-8-sig",
    )


def test_make_forecast_target_1s_shifts_300_seconds():
    n = 700
    df = pd.DataFrame({
        NOX_TARGET_COL: np.arange(n, dtype=float),
    })
    out = make_forecast_target_1s(df)
    # 5분 뒤 = 300초 뒤 → 마지막 300행 drop
    assert len(out) == n - FORECAST_HORIZON_SEC
    # 첫 행: 0초 시점, 타깃 = 300초 시점 NOx
    assert out[TARGET_COL].iloc[0] == 300.0
    assert out[NOX_TARGET_COL].iloc[0] == 0.0


def test_forecast_horizon_constant_is_300s():
    assert FORECAST_HORIZON_SEC == 300


def test_add_nox_lag_features_creates_3_columns():
    n = 1000
    df = pd.DataFrame({
        NOX_TARGET_COL: np.arange(n, dtype=float),
        "other": np.zeros(n),
    })
    out = add_nox_lag_features(df)
    for col in NOX_LAG_FEATURES:
        assert col in out.columns
    # 60초 lag: 60번째 행은 0, 61번째 행은 1, ...
    assert pd.isna(out["nox_lag_60s"].iloc[59])
    assert out["nox_lag_60s"].iloc[60] == 0.0
    assert out["nox_lag_60s"].iloc[100] == 40.0
    # 300초 lag
    assert pd.isna(out["nox_lag_300s"].iloc[299])
    assert out["nox_lag_300s"].iloc[300] == 0.0


def test_build_training_dataset_end_to_end(tmp_path: Path):
    from digital_twin.forecaster.preprocess import build_training_dataset

    csv_path = tmp_path / "synthetic.csv"
    # 15분 lag warmup + 5분 shift + 300초 NOx lag → 최소 25분+ 필요
    _make_synthetic_csv(csv_path, n_seconds=2400)  # 40분치

    X, y, meta = build_training_dataset(csv_path, subsample_sec=5)

    assert len(X) == len(y)
    assert len(X) > 0
    assert list(X.columns) == FEATURES
    assert y.name == TARGET_COL
    assert "npr_hinge_threshold" in meta
    assert "n_samples" in meta
    assert meta["subsample_sec"] == 5
    assert meta["resolution"] == "1s"
    # NOx lag 컬럼 포함 확인
    for col in NOX_LAG_FEATURES:
        assert col in X.columns
