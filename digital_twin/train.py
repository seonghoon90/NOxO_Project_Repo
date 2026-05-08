"""
digital_twin/train.py
=====================
NOx + 발전량 + 배기온도 예측 모델 학습.

모델 구조 (v2: 1분 집계 + Ridge·LGB 앙상블)
-------------------------------------------
- 입력 : 1초 시계열 → 1분(60행) 평균 집계
- 모델 : MultiOutput LightGBM + MultiOutput Ridge 가중 앙상블
         최종 = ENSEMBLE_W_RIDGE * Ridge + (1-ENSEMBLE_W_RIDGE) * LGB
- 근거 :
    * 1분 집계로 1초 자기상관 제거 → 분포 이동에 강건
    * Ridge(선형)는 학습 분포 외 외삽 가능, LGB(트리)는 비선형 보완
    * 검증 결과 NOx R² 0.4707 (1초 LGB) → 0.7051 (1분 앙상블) +49.8%
"""

import json
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from preprocess import (
    load_data, split_xy, aggregate_to_1min,
    FEATURES, TARGETS,
)

MODELS_DIR = Path(__file__).parent / "models"

# 앙상블 가중치 (검증된 최적값: 0.7 Ridge + 0.3 LGB → NOx R²=0.7051)
ENSEMBLE_W_RIDGE = 0.7
RIDGE_ALPHA      = 0.01


def build_lgb_model() -> MultiOutputRegressor:
    return MultiOutputRegressor(
        LGBMRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        ),
        n_jobs=-1,
    )


def build_ridge_model(alpha: float = RIDGE_ALPHA) -> MultiOutputRegressor:
    return MultiOutputRegressor(
        Pipeline([
            ("scaler", StandardScaler()),
            ("ridge",  Ridge(alpha=alpha)),
        ]),
        n_jobs=-1,
    )


def train_models(
    X_train: pd.DataFrame, y_train: pd.DataFrame
) -> tuple[MultiOutputRegressor, MultiOutputRegressor]:
    lgb_model   = build_lgb_model()
    ridge_model = build_ridge_model()
    lgb_model.fit(X_train, y_train)
    ridge_model.fit(X_train, y_train)
    return lgb_model, ridge_model


def predict_ensemble(
    lgb_model: MultiOutputRegressor,
    ridge_model: MultiOutputRegressor,
    X: pd.DataFrame,
    w_ridge: float = ENSEMBLE_W_RIDGE,
) -> np.ndarray:
    yp_lgb   = lgb_model.predict(X)
    yp_ridge = ridge_model.predict(X)
    return w_ridge * yp_ridge + (1 - w_ridge) * yp_lgb


def evaluate_ensemble(
    lgb_model: MultiOutputRegressor,
    ridge_model: MultiOutputRegressor,
    X: pd.DataFrame,
    y: pd.DataFrame,
    w_ridge: float = ENSEMBLE_W_RIDGE,
) -> dict:
    y_pred = predict_ensemble(lgb_model, ridge_model, X, w_ridge)
    results = {}
    for i, target in enumerate(TARGETS):
        results[target] = {
            "mae":  float(mean_absolute_error(y.iloc[:, i], y_pred[:, i])),
            "rmse": float(np.sqrt(mean_squared_error(y.iloc[:, i], y_pred[:, i]))),
            "r2":   float(r2_score(y.iloc[:, i], y_pred[:, i])),
        }
    return results


def save_artifacts(
    lgb_model: MultiOutputRegressor,
    ridge_model: MultiOutputRegressor,
    features: list,
    train_metrics_ens: dict,
    test_metrics_ens: dict,
    train_metrics_lgb: dict,
    test_metrics_lgb: dict,
    train_metrics_ridge: dict,
    test_metrics_ridge: dict,
    train_samples: int,
    test_samples: int,
    npr_hinge_threshold: float,
) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(lgb_model,   MODELS_DIR / "dt_lgb_model.pkl")
    joblib.dump(ridge_model, MODELS_DIR / "dt_ridge_model.pkl")
    metadata = {
        "model_type": "Ensemble: MultiOutput(LGBMRegressor) + MultiOutput(StandardScaler→Ridge)",
        "ensemble": {
            "w_ridge":  ENSEMBLE_W_RIDGE,
            "w_lgb":    1.0 - ENSEMBLE_W_RIDGE,
            "ridge_alpha": RIDGE_ALPHA,
        },
        "aggregation": "1min (60s mean)",
        "features": features,
        "targets": TARGETS,
        "n_features": len(features),
        "train_samples_1min": train_samples,
        "test_samples_1min":  test_samples,
        "feature_engineering": {
            "removed": ["IGCC.DeNOX.AIT_H1_902 (H1: 준누수 제외)"],
            "added_h5_npr": ["feat_NPR_avg", "feat_NPR_gap", "feat_NPR_hinge", "feat_NPR_x_NQJ"],
            "added_h3_nqj_lag": ["feat_NQJ_lag_1min", "feat_NQJ_lag_3min", "feat_NQJ_lag_5min"],
            "added_h4_ttxm": ["feat_TTXM_lag_1min", "feat_TTXM_roll_5min", "feat_TTXM_roll_15min"],
            "npr_hinge_threshold": npr_hinge_threshold,
        },
        "train_performance": {
            "ensemble": train_metrics_ens,
            "lgb_only": train_metrics_lgb,
            "ridge_only": train_metrics_ridge,
        },
        "test_performance": {
            "ensemble": test_metrics_ens,
            "lgb_only": test_metrics_lgb,
            "ridge_only": test_metrics_ridge,
        },
    }
    with open(MODELS_DIR / "dt_model_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    root = Path(__file__).parent.parent

    print("Loading train data (1초 → 1분 집계)...")
    train_df_1s, npr_threshold = load_data(root / "data" / "NOx_train_20250811_20250824.csv")
    print(f"  NPR hinge threshold (train median): {npr_threshold:.4f}")
    print(f"  1초 행수: {len(train_df_1s):,}")
    train_df = aggregate_to_1min(train_df_1s)
    print(f"  1분 행수: {len(train_df):,}")

    print("\nLoading test data...")
    test_df_1s, _ = load_data(
        root / "data" / "NOx_test_20250825.csv",
        npr_hinge_threshold=npr_threshold,   # 학습 기준값 고정
    )
    test_df = aggregate_to_1min(test_df_1s)
    print(f"  Test 1분 행수: {len(test_df):,}")

    X_train, y_train = split_xy(train_df)
    X_test,  y_test  = split_xy(test_df)
    print(f"\nFeatures: {len(FEATURES)} (RAW 39 + DERIVED 10)")
    print(f"Train: {len(X_train):,} 행 | Test: {len(X_test):,} 행 (모두 1분 집계)")

    print("\nTraining LightGBM + Ridge (MultiOutput)...")
    lgb_model, ridge_model = train_models(X_train, y_train)

    print("\nEvaluating...")
    # 앙상블
    train_metrics_ens = evaluate_ensemble(lgb_model, ridge_model, X_train, y_train)
    test_metrics_ens  = evaluate_ensemble(lgb_model, ridge_model, X_test,  y_test)
    # 단일 모델 비교용
    def _metrics(model, X, y):
        yp = model.predict(X)
        return {
            t: {
                "mae":  float(mean_absolute_error(y.iloc[:, i], yp[:, i])),
                "rmse": float(np.sqrt(mean_squared_error(y.iloc[:, i], yp[:, i]))),
                "r2":   float(r2_score(y.iloc[:, i], yp[:, i])),
            } for i, t in enumerate(TARGETS)
        }
    train_metrics_lgb   = _metrics(lgb_model,   X_train, y_train)
    test_metrics_lgb    = _metrics(lgb_model,   X_test,  y_test)
    train_metrics_ridge = _metrics(ridge_model, X_train, y_train)
    test_metrics_ridge  = _metrics(ridge_model, X_test,  y_test)

    target_labels = {
        "IGCC.DeNOX.AT_H1_901_PV": "NOx (ppm)",
        "IGCC.CC.G1.DWATT":        "발전량 (MW)",
        "IGCC.CC.G1.TTXM":         "배기가스온도 (°C)",
    }
    print(f"\n앙상블 가중치: Ridge={ENSEMBLE_W_RIDGE}, LGB={1-ENSEMBLE_W_RIDGE}")
    for target in TARGETS:
        label = target_labels[target]
        te_e  = test_metrics_ens[target]
        te_l  = test_metrics_lgb[target]
        te_r  = test_metrics_ridge[target]
        print(f"\n[{label}]")
        print(f"  Test  앙상블  MAE={te_e['mae']:.4f}  RMSE={te_e['rmse']:.4f}  R²={te_e['r2']:.4f}")
        print(f"  Test  LGB만   MAE={te_l['mae']:.4f}  RMSE={te_l['rmse']:.4f}  R²={te_l['r2']:.4f}")
        print(f"  Test  Ridge만 MAE={te_r['mae']:.4f}  RMSE={te_r['rmse']:.4f}  R²={te_r['r2']:.4f}")

    save_artifacts(
        lgb_model=lgb_model,
        ridge_model=ridge_model,
        features=X_train.columns.tolist(),
        train_metrics_ens=train_metrics_ens,
        test_metrics_ens=test_metrics_ens,
        train_metrics_lgb=train_metrics_lgb,
        test_metrics_lgb=test_metrics_lgb,
        train_metrics_ridge=train_metrics_ridge,
        test_metrics_ridge=test_metrics_ridge,
        train_samples=len(X_train),
        test_samples=len(X_test),
        npr_hinge_threshold=npr_threshold,
    )
    print("\nArtifacts saved to digital_twin/models/")
    print("  - dt_lgb_model.pkl   (MultiOutput LightGBM)")
    print("  - dt_ridge_model.pkl (MultiOutput Ridge)")
    print("  - dt_model_metadata.json")
