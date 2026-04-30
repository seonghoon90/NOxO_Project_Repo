import pytest
import pandas as pd
from pathlib import Path
from lightgbm import LGBMRegressor
from sklearn.multioutput import MultiOutputRegressor
from preprocess import load_data, split_xy, FEATURES, TARGETS

DATA_DIR = Path(__file__).parent.parent.parent / "data"
TRAIN_FILE = DATA_DIR / "NOx_train_20250811_20250824.csv"

pytestmark = pytest.mark.skipif(
    not TRAIN_FILE.exists(),
    reason="Real data file not available"
)


@pytest.fixture(scope="module")
def tiny_model():
    df = load_data(TRAIN_FILE)
    X, y = split_xy(df.head(200))
    model = MultiOutputRegressor(
        LGBMRegressor(n_estimators=10, random_state=42, verbose=-1)
    )
    model.fit(X, y)
    return model


@pytest.fixture(scope="module")
def sample_input_dict():
    df = load_data(TRAIN_FILE)
    row = df[FEATURES].iloc[0]
    return {col: float(row[col]) for col in FEATURES}


def test_predict_returns_dict(tiny_model, sample_input_dict):
    from predict import predict
    result = predict(tiny_model, sample_input_dict)
    assert isinstance(result, dict)


def test_predict_has_all_three_targets(tiny_model, sample_input_dict):
    from predict import predict
    result = predict(tiny_model, sample_input_dict)
    for target in TARGETS:
        assert target in result, f"Missing target: {target}"


def test_predict_all_values_are_float(tiny_model, sample_input_dict):
    from predict import predict
    result = predict(tiny_model, sample_input_dict)
    for target in TARGETS:
        assert isinstance(result[target], float), f"Non-float: {target}"


def test_predict_accepts_dataframe(tiny_model):
    from predict import predict
    df = load_data(TRAIN_FILE).head(1)
    result = predict(tiny_model, df)
    assert isinstance(result, dict)
    for target in TARGETS:
        assert target in result


def test_predict_nox_is_non_negative(tiny_model, sample_input_dict):
    from predict import predict
    result = predict(tiny_model, sample_input_dict)
    assert result["IGCC.DeNOX.AT_H1_901_PV"] >= 0


def test_load_model_raises_on_missing_file():
    from predict import load_model
    with pytest.raises(FileNotFoundError):
        load_model(Path("nonexistent/model.pkl"))
