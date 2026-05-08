"""
digital_twin/predict.py
========================
추론 인터페이스 (v2: 1분 집계 + Ridge·LGB 앙상블).

입력 방식
---------
1. 원시 센서값 dict (RAW_FEATURES 39개) + 최근 시계열 버퍼(recent_df)
   - recent_df는 최소 60행(1분치) 이상의 1초 시계열을 권장
   - 자동으로 파생 피처 계산 + 1분 평균 집계 후 예측

2. 1분 집계된 단일 행 (FEATURES 49개 모두 포함)
   - 외부에서 이미 1분 집계 + 파생 피처 계산을 끝낸 경우

추론 동작
---------
- 두 모델(MultiOutput LGB, MultiOutput Ridge) 모두 예측
- metadata의 ensemble.w_ridge 가중치로 가중 평균
- 결과는 1분 시점의 NOx/DWATT/TTXM 예측값
"""

import json
import warnings
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from preprocess import (
    FEATURES, RAW_FEATURES, TARGETS,
    add_derived_features, aggregate_to_1min,
)

MODELS_DIR = Path(__file__).parent / "models"

# 앙상블 가중치 기본값 (metadata 없을 때 fallback)
DEFAULT_W_RIDGE = 0.7


def load_models(
    lgb_path: Path | None = None,
    ridge_path: Path | None = None,
) -> tuple[object, object]:
    lgb_p   = Path(lgb_path)   if lgb_path   else MODELS_DIR / "dt_lgb_model.pkl"
    ridge_p = Path(ridge_path) if ridge_path else MODELS_DIR / "dt_ridge_model.pkl"
    if not lgb_p.exists():
        raise FileNotFoundError(f"LightGBM model not found: {lgb_p}")
    if not ridge_p.exists():
        raise FileNotFoundError(f"Ridge model not found: {ridge_p}")
    return joblib.load(lgb_p), joblib.load(ridge_p)


# 하위 호환: 단일 모델 로더 (deprecated)
def load_model(model_path: Path | None = None) -> tuple[object, object]:
    """하위 호환용. 앙상블 모델 (LGB, Ridge) 튜플 반환."""
    return load_models()


def _load_metadata() -> dict:
    """metadata.json 로드. 없으면 빈 dict."""
    meta_path = MODELS_DIR / "dt_model_metadata.json"
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_npr_threshold() -> float:
    meta = _load_metadata()
    return meta.get("feature_engineering", {}).get("npr_hinge_threshold", 0.0)


def _load_w_ridge() -> float:
    meta = _load_metadata()
    return meta.get("ensemble", {}).get("w_ridge", DEFAULT_W_RIDGE)


def predict(
    model: object | tuple,
    inputs: dict | pd.DataFrame,
    recent_df: pd.DataFrame | None = None,
) -> dict:
    """NOx, 발전량, 배기가스온도 예측.

    Parameters
    ----------
    model:
        load_models() 또는 load_model()로 로드한 (lgb_model, ridge_model) 튜플.
        하위 호환을 위해 단일 모델도 받지만, 그 경우 LGB만 사용 (앙상블 없음).
    inputs:
        현재 시점 센서값.
        - dict: RAW_FEATURES 39개 또는 FEATURES 49개 포함
        - pd.DataFrame: 1행 이상 (마지막 행 사용)
    recent_df:
        최근 1분(60행) 이상의 1초 시계열 DataFrame.
        RAW_FEATURES 컬럼 포함 필요. 없으면 단일 행으로 추론(정확도 저하 경고).

    Returns
    -------
    dict
        {타깃명: 예측값} 형태.
    """
    # 1. model unpack (앙상블 / 단일 모두 지원)
    if isinstance(model, tuple) and len(model) == 2:
        lgb_model, ridge_model = model
        is_ensemble = True
        w_ridge = _load_w_ridge()
    else:
        lgb_model = model
        ridge_model = None
        is_ensemble = False
        w_ridge = 0.0

    # 2. inputs → 1행 DataFrame
    if isinstance(inputs, dict):
        row = pd.DataFrame([inputs])
    else:
        row = inputs.iloc[[-1]].copy()

    # 3. 이미 FEATURES 모두 있고 단일 행이면, 1분 집계 단계로 간주
    if all(f in row.columns for f in FEATURES) and recent_df is None:
        df_feat = row[FEATURES]
        return _ensemble_predict(lgb_model, ridge_model, df_feat,
                                 is_ensemble, w_ridge)

    # 4. RAW_FEATURES 검증
    missing_raw = set(RAW_FEATURES) - set(row.columns)
    if missing_raw:
        raise ValueError(f"입력에 원시 피처가 없습니다: {sorted(missing_raw)}")

    npr_threshold = _load_npr_threshold()

    if recent_df is not None:
        # add_derived_features는 RAW_FEATURES 외에 TTXM(타깃이지만 lag용 입력)도 필요
        TTXM_COL = "IGCC.CC.G1.TTXM"
        if TTXM_COL not in recent_df.columns:
            raise ValueError(
                f"recent_df에 {TTXM_COL} 컬럼이 필요합니다 "
                "(과거 관측 TTXM 값으로 lag/rolling 피처 계산)."
            )
        cols_needed = RAW_FEATURES + [TTXM_COL]
        # 현재 row에 TTXM 없으면 직전 관측값(forward fill)으로 보강
        row_aug = row[RAW_FEATURES].copy()
        row_aug[TTXM_COL] = (
            row[TTXM_COL].values[0] if TTXM_COL in row.columns
            else recent_df[TTXM_COL].iloc[-1]
        )
        buf = pd.concat(
            [recent_df[cols_needed], row_aug[cols_needed]],
            ignore_index=True,
        )
        buf, _ = add_derived_features(buf, npr_hinge_threshold=npr_threshold)
        # NaN 행 제거 (lag/rolling warm-up 구간)
        buf_valid = buf.dropna(subset=FEATURES)

        if len(buf_valid) >= 60:
            # 충분한 데이터 — 마지막 60행으로 1분 집계
            agg = aggregate_to_1min(buf_valid.tail(60))
            df_feat = agg.iloc[[-1]][FEATURES]
        elif len(buf_valid) > 0:
            # 일부 warm-up 부족 — 사용 가능한 마지막 행들 평균 (1분 집계 대용)
            warnings.warn(
                f"recent_df의 유효 행수가 부족합니다 "
                f"(필요: 60행, 유효: {len(buf_valid)}행, 전체: {len(buf)}행). "
                "사용 가능 행들의 평균으로 추론 — 정확도가 낮아질 수 있습니다.",
                UserWarning, stacklevel=2,
            )
            df_feat = pd.DataFrame([buf_valid[FEATURES].mean()])
        else:
            # warm-up 완전 부족 — 마지막 행을 ffill로 사용
            warnings.warn(
                f"recent_df warm-up 부족(전체 {len(buf)}행). "
                f"lag 피처 계산 불가 — 단일 1초 행 폴백.",
                UserWarning, stacklevel=2,
            )
            buf_ff = buf.ffill().bfill().fillna(0)
            df_feat = buf_ff.iloc[[-1]][FEATURES]
    else:
        # recent_df 없음 — 단일 행 모드 (lag 피처 부정확)
        warnings.warn(
            "recent_df가 없어 단일 1초 행으로 추론합니다. "
            "lag 피처(feat_NQJ_lag_*, feat_TTXM_*)가 부정확하고, "
            "1분 집계 노이즈 제거 효과가 사라져 정확도가 크게 낮아집니다.",
            UserWarning, stacklevel=2,
        )
        # add_derived_features가 TTXM을 요구 — 입력에 없으면 0으로 채움(이후 fillna로 대체)
        TTXM_COL = "IGCC.CC.G1.TTXM"
        row_aug = row[RAW_FEATURES].copy()
        row_aug[TTXM_COL] = (
            row[TTXM_COL].values[0] if TTXM_COL in row.columns else 0.0
        )
        buf, _ = add_derived_features(row_aug, npr_hinge_threshold=npr_threshold)
        for col in FEATURES:
            if col not in buf.columns or buf[col].isna().any():
                if "NQJ" in col:
                    buf[col] = row["IGCC.CC.G1.NQJ"].values[0]
                elif "TTXM" in col:
                    buf[col] = row_aug[TTXM_COL].values[0]
                else:
                    buf[col] = 0.0
        df_feat = buf[FEATURES]

    return _ensemble_predict(lgb_model, ridge_model, df_feat,
                             is_ensemble, w_ridge)


def _ensemble_predict(lgb_model, ridge_model, X, is_ensemble, w_ridge):
    yp_lgb = lgb_model.predict(X)
    if is_ensemble and ridge_model is not None:
        yp_ridge = ridge_model.predict(X)
        y_pred = w_ridge * yp_ridge + (1 - w_ridge) * yp_lgb
    else:
        y_pred = yp_lgb
    return {t: float(y_pred[0, i]) for i, t in enumerate(TARGETS)}
