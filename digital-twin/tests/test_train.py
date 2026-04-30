import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.multioutput import MultiOutputRegressor
from preprocess import load_data, split_xy, FEATURES, TARGETS

DATA_DIR = Path(__file__).parent.parent.parent / "data"
TRAIN_FILE = DATA_DIR / "NOx_train_20250811_20250824.csv"

pytestmark = pytest.mark.skipif(
    not TRAIN_FILE.exists(),
    reason="Real data file not available"
)


@pytest.fixture(scope="module")
def small_xy():
    df = load_data(TRAIN_FILE)
    X, y = split_xy(df.head(200))
    return X, y


def test_build_model_returns_multioutput_regressor():
    from train import build_model
    model = build_model()
    assert isinstance(model, MultiOutputRegressor)


def test_train_model_has_estimators_after_fit(small_xy):
    from train import train_model
    X, y = small_xy
    model = train_model(X, y)
    assert hasattr(model, "estimators_")
    assert len(model.estimators_) == len(TARGETS)


def test_train_model_predict_shape(small_xy):
    from train import train_model
    X, y = small_xy
    model = train_model(X, y)
    y_pred = model.predict(X)
    assert y_pred.shape == (len(X), len(TARGETS))


def test_evaluate_model_has_all_targets(small_xy):
    from train import train_model, evaluate_model
    X, y = small_xy
    model = train_model(X, y)
    metrics = evaluate_model(model, X, y)
    for target in TARGETS:
        assert target in metrics, f"Missing target in metrics: {target}"


def test_evaluate_model_has_mae_rmse_r2(small_xy):
    from train import train_model, evaluate_model
    X, y = small_xy
    model = train_model(X, y)
    metrics = evaluate_model(model, X, y)
    for target in TARGETS:
        assert "mae" in metrics[target]
        assert "rmse" in metrics[target]
        assert "r2" in metrics[target]


def test_evaluate_model_mae_is_positive(small_xy):
    from train import train_model, evaluate_model
    X, y = small_xy
    model = train_model(X, y)
    metrics = evaluate_model(model, X, y)
    for target in TARGETS:
        assert metrics[target]["mae"] >= 0


def test_evaluate_model_r2_leq_1(small_xy):
    from train import train_model, evaluate_model
    X, y = small_xy
    model = train_model(X, y)
    metrics = evaluate_model(model, X, y)
    for target in TARGETS:
        assert metrics[target]["r2"] <= 1.0001
