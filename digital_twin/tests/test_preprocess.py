import pandas as pd
import pytest
from pathlib import Path
from preprocess import load_data, split_xy, train_val_split, FEATURES, TARGETS

DATA_DIR = Path(__file__).parent.parent.parent / "data"
TRAIN_FILE = DATA_DIR / "NOx_train_20250811_20250824.csv"

pytestmark = pytest.mark.skipif(
    not TRAIN_FILE.exists(),
    reason="Real data file not available"
)


def test_feature_count():
    assert len(FEATURES) == 40


def test_target_count():
    assert len(TARGETS) == 3


def test_targets_are_correct():
    assert "IGCC.DeNOX.AT_H1_901_PV" in TARGETS
    assert "IGCC.CC.G1.DWATT" in TARGETS
    assert "IGCC.CC.G1.TTXM" in TARGETS


def test_load_data_returns_dataframe():
    df = load_data(TRAIN_FILE)
    assert isinstance(df, pd.DataFrame)


def test_load_data_has_correct_columns():
    df = load_data(TRAIN_FILE)
    for col in FEATURES + TARGETS:
        assert col in df.columns, f"Missing column: {col}"


def test_load_data_no_nulls():
    df = load_data(TRAIN_FILE)
    assert df.isnull().sum().sum() == 0


def test_load_data_all_numeric():
    df = load_data(TRAIN_FILE)
    for col in FEATURES + TARGETS:
        assert pd.api.types.is_float_dtype(df[col]), f"Non-float: {col}"


def test_split_xy_feature_columns():
    df = load_data(TRAIN_FILE)
    X, y = split_xy(df)
    assert list(X.columns) == FEATURES


def test_split_xy_target_columns():
    df = load_data(TRAIN_FILE)
    X, y = split_xy(df)
    assert list(y.columns) == TARGETS


def test_split_xy_same_length():
    df = load_data(TRAIN_FILE)
    X, y = split_xy(df)
    assert len(X) == len(y) == len(df)


def test_train_val_split_sizes():
    df = load_data(TRAIN_FILE)
    train_df, val_df = train_val_split(df, val_ratio=0.2)
    assert len(train_df) + len(val_df) == len(df)
    assert len(val_df) == pytest.approx(len(df) * 0.2, abs=1)


def test_train_val_split_preserves_order():
    df = load_data(TRAIN_FILE)
    train_df, val_df = train_val_split(df, val_ratio=0.2)
    split_idx = len(train_df)
    assert train_df.index.tolist() == df.index[:split_idx].tolist()
    assert val_df.index.tolist() == df.index[split_idx:].tolist()


@pytest.mark.skipif(False, reason="always run")
def test_load_data_skips_metadata_rows(tmp_path):
    header = ["TagName"] + FEATURES + TARGETS
    rows = [
        ["Description"] + ["desc"] * (len(FEATURES) + len(TARGETS)),
        ["Units"] + ["unit"] * (len(FEATURES) + len(TARGETS)),
        ["Plot Min"] + ["0"] * (len(FEATURES) + len(TARGETS)),
        ["Plot Max"] + ["100"] * (len(FEATURES) + len(TARGETS)),
        ["row1"] + ["1.0"] * (len(FEATURES) + len(TARGETS)),
        ["row2"] + ["2.0"] * (len(FEATURES) + len(TARGETS)),
    ]
    csv_path = tmp_path / "test.csv"
    with open(csv_path, "w") as f:
        f.write(",".join(header) + "\n")
        for row in rows:
            f.write(",".join(row) + "\n")
    df = load_data(csv_path)
    assert len(df) == 2
    assert list(df.columns) == FEATURES + TARGETS


@pytest.mark.skipif(False, reason="always run")
def test_load_data_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        load_data(Path("/nonexistent/file.csv"))


@pytest.mark.skipif(False, reason="always run")
def test_train_val_split_invalid_ratio_raises():
    df = pd.DataFrame({"a": range(10)})
    with pytest.raises(ValueError):
        train_val_split(df, val_ratio=20)
