"""5분 NOx 예측 모델 학습 스크립트 (LightGBM + Ridge 앙상블).

v2.2 변경:
- Ridge + LightGBM 앙상블 (Forecast01 패턴)
- 최종 = ENSEMBLE_W_RIDGE * Ridge + (1 - ENSEMBLE_W_RIDGE) * LGB
- 두 모델 모두 같은 .pkl 묶음에 저장

CLI:
    python -m digital_twin.forecaster.train --data data/raw/x.csv --output digital_twin/forecaster/models/
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from digital_twin.forecaster.ensemble import EnsembleForecaster
from digital_twin.forecaster.preprocess import (
    FEATURES,
    FORECAST_HORIZON_MIN,
    FORECAST_HORIZON_SEC,
    build_training_dataset,
)

MODEL_FILENAME = "forecaster_lgb_model.pkl"  # 호환성 (predict.py 기본 경로)
META_FILENAME = "forecaster_metadata.json"

# 앙상블 가중치 — holdout grid search 결과 w_ridge=0.8이 최적 (R² 0.59)
# Ridge가 외삽에 강해 분포 이동에 robust, LGB는 비선형 미세조정용
ENSEMBLE_W_RIDGE: float = 0.8
RIDGE_ALPHA: float = 1.0


def _metrics(y_true, y_pred) -> dict:
    if len(y_true) == 0:
        return {"r2": None, "mae": None, "rmse": None}
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
    }


def train_forecaster(
    csv_path: str | Path,
    output_dir: str | Path,
    val_ratio: float = 0.2,
    n_estimators: int = 300,
    max_depth: int = 6,
    learning_rate: float = 0.05,
    random_state: int = 42,
    subsample_sec: int = 5,
    ensemble_w_ridge: float = ENSEMBLE_W_RIDGE,
    ridge_alpha: float = RIDGE_ALPHA,
) -> dict:
    """CSV에서 5분 NOx 예측 Ridge+LGB 앙상블 학습 후 .pkl/.json 저장."""
    csv_path = Path(csv_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    X, y, pre_meta = build_training_dataset(csv_path, subsample_sec=subsample_sec)
    n = len(X)
    if n < 10:
        raise ValueError(f"학습 샘플 부족: {n}행. 최소 10행 필요.")

    split = int(n * (1.0 - val_ratio))
    X_tr, X_val = X.iloc[:split], X.iloc[split:]
    y_tr, y_val = y.iloc[:split], y.iloc[split:]

    # ── LightGBM ──
    lgb = LGBMRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=random_state,
        verbose=-1,
    )
    lgb.fit(X_tr, y_tr)

    # ── Ridge (StandardScaler 필수) ──
    ridge_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=ridge_alpha, random_state=random_state)),
    ])
    ridge_pipe.fit(X_tr, y_tr)

    # ── 앙상블 ──
    ens = EnsembleForecaster(ridge_pipe=ridge_pipe, lgb=lgb, w_ridge=ensemble_w_ridge)

    # 메트릭: 각 모델 + 앙상블
    yp_lgb_tr = lgb.predict(X_tr)
    yp_ridge_tr = ridge_pipe.predict(X_tr)
    yp_ens_tr = ens.predict(X_tr)

    yp_lgb_val = lgb.predict(X_val) if len(X_val) > 0 else np.array([])
    yp_ridge_val = ridge_pipe.predict(X_val) if len(X_val) > 0 else np.array([])
    yp_ens_val = ens.predict(X_val) if len(X_val) > 0 else np.array([])

    model_path = output_dir / MODEL_FILENAME
    meta_path = output_dir / META_FILENAME
    joblib.dump(ens, model_path)

    metadata = {
        "model_type": "ensemble_ridge_lgb",
        "horizon_minutes": FORECAST_HORIZON_MIN,
        "horizon_seconds": FORECAST_HORIZON_SEC,
        "subsample_sec": subsample_sec,
        "resolution": pre_meta.get("resolution", "1s"),
        "n_features": len(FEATURES),
        "features": FEATURES,
        "n_train": int(len(X_tr)),
        "n_val": int(len(X_val)),
        "train_metrics": _metrics(y_tr, yp_ens_tr),
        "val_metrics": _metrics(y_val, yp_ens_val),
        "train_metrics_lgb": _metrics(y_tr, yp_lgb_tr),
        "val_metrics_lgb": _metrics(y_val, yp_lgb_val),
        "train_metrics_ridge": _metrics(y_tr, yp_ridge_tr),
        "val_metrics_ridge": _metrics(y_val, yp_ridge_val),
        "ensemble_w_ridge": ensemble_w_ridge,
        "npr_hinge_threshold": pre_meta["npr_hinge_threshold"],
        "hyperparameters": {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "ridge_alpha": ridge_alpha,
            "random_state": random_state,
        },
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "source_csv": str(csv_path),
    }
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "model_path": str(model_path),
        "metadata_path": str(meta_path),
        "metrics": {"train": metadata["train_metrics"], "val": metadata["val_metrics"]},
        "metrics_lgb": {"train": metadata["train_metrics_lgb"], "val": metadata["val_metrics_lgb"]},
        "metrics_ridge": {"train": metadata["train_metrics_ridge"], "val": metadata["val_metrics_ridge"]},
    }


def _build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="5분 NOx 예측 모델 학습 (Ridge+LGB 앙상블)")
    p.add_argument("--data", required=True, help="1초 raw CSV 경로")
    p.add_argument("--output", default="digital_twin/forecaster/models/", help="모델 저장 디렉토리")
    p.add_argument("--val-ratio", type=float, default=0.2)
    p.add_argument("--n-estimators", type=int, default=300)
    p.add_argument("--max-depth", type=int, default=6)
    p.add_argument("--learning-rate", type=float, default=0.05)
    p.add_argument("--subsample-sec", type=int, default=5,
                   help="1초 데이터 등간격 subsample (기본 5초)")
    p.add_argument("--ensemble-w-ridge", type=float, default=ENSEMBLE_W_RIDGE,
                   help="앙상블에서 Ridge 가중치 (LGB=1-w)")
    p.add_argument("--ridge-alpha", type=float, default=RIDGE_ALPHA)
    return p


def main() -> None:
    args = _build_cli().parse_args()
    result = train_forecaster(
        csv_path=args.data,
        output_dir=args.output,
        val_ratio=args.val_ratio,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
        subsample_sec=args.subsample_sec,
        ensemble_w_ridge=args.ensemble_w_ridge,
        ridge_alpha=args.ridge_alpha,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
