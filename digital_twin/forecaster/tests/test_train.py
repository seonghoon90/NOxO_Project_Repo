import json
from pathlib import Path

import joblib

from digital_twin.forecaster.tests.test_preprocess import _make_synthetic_csv


def test_train_writes_model_and_metadata(tmp_path: Path):
    from digital_twin.forecaster.train import train_forecaster

    csv = tmp_path / "data.csv"
    _make_synthetic_csv(csv, n_seconds=1800)

    out_dir = tmp_path / "models"
    out_dir.mkdir()

    result = train_forecaster(
        csv_path=csv,
        output_dir=out_dir,
        val_ratio=0.2,
        n_estimators=20,
    )

    model_path = out_dir / "forecaster_lgb_model.pkl"
    meta_path = out_dir / "forecaster_metadata.json"

    assert model_path.exists()
    assert meta_path.exists()

    model = joblib.load(model_path)
    assert hasattr(model, "predict")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["horizon_minutes"] == 5
    assert meta["model_type"] == "ensemble_ridge_lgb"
    assert "ensemble_w_ridge" in meta
    assert "n_features" in meta
    assert "train_metrics" in meta
    assert "val_metrics" in meta
    assert "npr_hinge_threshold" in meta
    assert "trained_at" in meta

    assert result["model_path"] == str(model_path)
    assert result["metadata_path"] == str(meta_path)
