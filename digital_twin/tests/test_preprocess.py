import pandas as pd
import pytest
from pathlib import Path
from preprocess import (
    load_data, split_xy, train_val_split,
    FEATURES, RAW_FEATURES, DERIVED_FEATURES, TARGETS,
    add_derived_features, aggregate_to_1min,
)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
TRAIN_FILE = DATA_DIR / "NOx_train_20250811_20250824.csv"

pytestmark = pytest.mark.skipif(
    not TRAIN_FILE.exists(),
    reason="Real data file not available"
)


def test_raw_feature_count():
    """원시 피처는 39개 (O2 제외)."""
    assert len(RAW_FEATURES) == 39


def test_o2_not_in_features():
    """O2 (AIT_H1_902) 가 피처에 없어야 한다 — H1 준누수 제외."""
    assert "IGCC.DeNOX.AIT_H1_902" not in FEATURES


def test_derived_feature_count():
    """파생 피처 10개 (H3×3 + H4×3 + H5×4)."""
    assert len(DERIVED_FEATURES) == 10


def test_total_feature_count():
    """전체 피처 49개 (RAW 39 + DERIVED 10)."""
    assert len(FEATURES) == 49


def test_target_count():
    assert len(TARGETS) == 3


def test_targets_are_correct():
    assert "IGCC.DeNOX.AT_H1_901_PV" in TARGETS
    assert "IGCC.CC.G1.DWATT" in TARGETS
    assert "IGCC.CC.G1.TTXM" in TARGETS


def test_load_data_returns_dataframe():
    df, _ = load_data(TRAIN_FILE)
    assert isinstance(df, pd.DataFrame)


def test_load_data_has_correct_columns():
    df, _ = load_data(TRAIN_FILE)
    for col in FEATURES + TARGETS:
        assert col in df.columns, f"Missing column: {col}"


def test_load_data_no_nulls():
    df, _ = load_data(TRAIN_FILE)
    assert df[FEATURES + TARGETS].isnull().sum().sum() == 0


def test_load_data_all_numeric():
    df, _ = load_data(TRAIN_FILE)
    for col in FEATURES + TARGETS:
        assert pd.api.types.is_float_dtype(df[col]), f"Non-float: {col}"


def test_split_xy_feature_columns():
    df, _ = load_data(TRAIN_FILE)
    X, y = split_xy(df)
    assert list(X.columns) == FEATURES


def test_split_xy_target_columns():
    df, _ = load_data(TRAIN_FILE)
    X, y = split_xy(df)
    assert list(y.columns) == TARGETS


def test_split_xy_same_length():
    df, _ = load_data(TRAIN_FILE)
    X, y = split_xy(df)
    assert len(X) == len(y) == len(df)


def test_train_val_split_sizes():
    df, _ = load_data(TRAIN_FILE)
    train_df, val_df = train_val_split(df, val_ratio=0.2)
    assert len(train_df) + len(val_df) == len(df)
    assert len(val_df) == pytest.approx(len(df) * 0.2, abs=1)


def test_train_val_split_preserves_order():
    df, _ = load_data(TRAIN_FILE)
    train_df, val_df = train_val_split(df, val_ratio=0.2)
    split_idx = len(train_df)
    assert train_df.index.tolist() == df.index[:split_idx].tolist()
    assert val_df.index.tolist() == df.index[split_idx:].tolist()


def test_npr_hinge_threshold_returned():
    """load_data가 NPR hinge 임계값을 반환해야 한다."""
    _, threshold = load_data(TRAIN_FILE)
    assert isinstance(threshold, float)
    assert threshold > 0


@pytest.mark.skipif(False, reason="always run")
def test_load_data_skips_metadata_rows(tmp_path):
    """CSV 헤더 4행(Description/Units/Min/Max)을 건너뛰어야 한다."""
    # 합성 CSV: RAW_FEATURES + TARGETS만 포함 (파생 피처는 load_data가 계산)
    # lag warm-up 때문에 충분한 행 수(600)가 필요
    import numpy as np
    header = ["TagName"] + RAW_FEATURES + TARGETS
    n_rows = 600
    rng = np.random.default_rng(0)
    data_rows = rng.random((n_rows, len(RAW_FEATURES) + len(TARGETS))).tolist()

    csv_path = tmp_path / "test.csv"
    with open(csv_path, "w") as f:
        f.write(",".join(header) + "\n")
        for meta in [["Description"], ["Units"], ["Plot Min"], ["Plot Max"]]:
            f.write(",".join(meta + ["x"] * (len(RAW_FEATURES) + len(TARGETS))) + "\n")
        for i, row in enumerate(data_rows):
            f.write(f"row{i}," + ",".join(f"{v:.4f}" for v in row) + "\n")

    df, threshold = load_data(csv_path)
    # lag warm-up으로 일부 행 제거되므로 < 600
    assert len(df) < n_rows
    assert len(df) > 0
    assert all(col in df.columns for col in FEATURES + TARGETS)


@pytest.mark.skipif(False, reason="always run")
def test_load_data_raises_on_missing_file():
    import pytest as _pytest
    with _pytest.raises(FileNotFoundError):
        load_data(Path("/nonexistent/file.csv"))


@pytest.mark.skipif(False, reason="always run")
def test_train_val_split_invalid_ratio_raises():
    df = pd.DataFrame({"a": range(10)})
    import pytest as _pytest
    with _pytest.raises(ValueError):
        train_val_split(df, val_ratio=20)


@pytest.mark.skipif(False, reason="always run")
def test_aggregate_to_1min_shape():
    """1분 집계는 60행 → 1행으로 압축."""
    import numpy as np
    n = 600  # 10분치 1초 데이터
    df = pd.DataFrame({
        "a": np.arange(n, dtype=float),
        "b": np.arange(n, dtype=float) * 2.0,
    })
    out = aggregate_to_1min(df)
    assert len(out) == 10  # 600/60 = 10
    # 첫 1분 평균 = (0+1+...+59)/60 = 29.5
    assert abs(out["a"].iloc[0] - 29.5) < 1e-9
    # 두 번째 1분 평균 = 60~119 → 89.5
    assert abs(out["a"].iloc[1] - 89.5) < 1e-9


@pytest.mark.skipif(False, reason="always run")
def test_aggregate_to_1min_truncates_partial():
    """60의 배수가 아닌 행은 잘려서 집계됨."""
    import numpy as np
    df = pd.DataFrame({"a": np.arange(125, dtype=float)})
    out = aggregate_to_1min(df)
    assert len(out) == 2  # 125 // 60 = 2 (마지막 5행 버려짐)


@pytest.mark.skipif(False, reason="always run")
def test_aggregate_to_1min_too_short_raises():
    """60행 미만이면 예외."""
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    with pytest.raises(ValueError):
        aggregate_to_1min(df)


@pytest.mark.skipif(False, reason="always run")
def test_add_derived_features_columns():
    """add_derived_features가 10개 파생 피처를 추가해야 한다."""
    import numpy as np
    n = 400
    rng = np.random.default_rng(42)
    raw = {col: rng.random(n) for col in RAW_FEATURES + TARGETS}
    df_in = pd.DataFrame(raw)
    df_out, threshold = add_derived_features(df_in)
    for feat in DERIVED_FEATURES:
        assert feat in df_out.columns, f"파생 피처 누락: {feat}"
    assert isinstance(threshold, float)
