"""더미 모델 fixture 단독 검증 — Task 0.2."""

import joblib


def test_dummy_models_dir_creates_three_files(dummy_models_dir):
    assert (dummy_models_dir / "dt_lgb_model.pkl").exists()
    assert (dummy_models_dir / "dt_ridge_model.pkl").exists()
    assert (dummy_models_dir / "dt_model_metadata.json").exists()


def test_dummy_models_are_fitted(dummy_models_dir):
    lgb = joblib.load(dummy_models_dir / "dt_lgb_model.pkl")
    ridge = joblib.load(dummy_models_dir / "dt_ridge_model.pkl")
    assert hasattr(lgb, "estimators_")
    assert hasattr(ridge, "estimators_")
