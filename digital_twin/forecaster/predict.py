"""5분 NOx 예측 추론 인터페이스 (v2: 1초 단위 + NOx lag).

Backend `MLForecaster`가 본 모듈의 `load_model`/`predict`를 호출.
recent_df의 마지막 시점(t)에서 1초 단위 피처를 계산해 5분 뒤 NOx 단발 예측.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import joblib
import pandas as pd

from digital_twin.forecaster.ensemble import EnsembleForecaster  # noqa: F401 (pickle용)
from digital_twin.forecaster.preprocess import (
    FEATURES,
    NOX_TARGET_COL,
    RAW_FEATURES,
    add_derived_features,
    add_extended_features,
    add_generic_features,
    add_interaction_features,
    add_nox_lag_features,
    add_time_features,
)

MODELS_DIR = Path(__file__).parent / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "forecaster_lgb_model.pkl"
DEFAULT_META_PATH = MODELS_DIR / "forecaster_metadata.json"

TTXM_COL = "IGCC.CC.G1.TTXM"
DWATT_COL = "IGCC.CC.G1.DWATT"  # 확장 피처 DWATT_diff_60s 입력용 (TARGETS 소속)
O2_DIRECT_COL = "IGCC.DeNOX.AIT_H1_902"  # v2.7: 직접 O2 센서 (선택적)
# NOx lag warmup (300초) + 기존 TTXM 15분 rolling warmup → 추론에 최소 900초 권장
MIN_RECENT_ROWS = 900


class LoadedForecaster:
    """학습된 LGB 모델 + 메타데이터 묶음."""

    def __init__(self, model, metadata: dict):
        self.model = model
        self.metadata = metadata
        self.npr_threshold = float(metadata.get("npr_hinge_threshold", 0.0))


def load_model(
    model_path: str | Path | None = None,
    metadata_path: str | Path | None = None,
) -> LoadedForecaster:
    mp = Path(model_path) if model_path else DEFAULT_MODEL_PATH
    metap = Path(metadata_path) if metadata_path else DEFAULT_META_PATH
    if not mp.exists():
        raise FileNotFoundError(f"Forecaster model not found: {mp}")
    if not metap.exists():
        raise FileNotFoundError(f"Forecaster metadata not found: {metap}")
    model = joblib.load(mp)
    metadata = json.loads(Path(metap).read_text(encoding="utf-8"))
    return LoadedForecaster(model=model, metadata=metadata)


def predict(loaded: LoadedForecaster, recent_df: pd.DataFrame) -> float:
    """최근 1초 시계열로 5분 뒤 NOx 예측.

    recent_df: 1초 raw 시계열. RAW_FEATURES + TTXM + NOx 컬럼 필요.
    15분(900행) 이상 권장 (lag/rolling warmup).
    """
    missing_raw = set(RAW_FEATURES) - set(recent_df.columns)
    if missing_raw:
        raise ValueError(f"recent_df에 원시 피처 누락: {sorted(missing_raw)}")
    if TTXM_COL not in recent_df.columns:
        raise ValueError(f"recent_df에 {TTXM_COL} 컬럼이 필요합니다 (lag 입력).")
    if NOX_TARGET_COL not in recent_df.columns:
        raise ValueError(
            f"recent_df에 {NOX_TARGET_COL} (NOx) 컬럼이 필요합니다 "
            "(NOx lag/rolling 피처 계산용)."
        )
    if DWATT_COL not in recent_df.columns:
        raise ValueError(
            f"recent_df에 {DWATT_COL} (발전량) 컬럼이 필요합니다 "
            "(DWATT_diff_60s 확장 피처 계산용)."
        )

    # O2 컬럼은 v2.7 모델 입력이지만 누락 시 0으로 폴백 (운영 환경 호환)
    cols_needed = RAW_FEATURES + [TTXM_COL, NOX_TARGET_COL, DWATT_COL]
    cols_needed = [c for c in cols_needed if c in recent_df.columns]
    if O2_DIRECT_COL not in recent_df.columns:
        warnings.warn(
            f"recent_df에 {O2_DIRECT_COL} 누락 — 0으로 폴백 (v2.7 모델 정확도 저하).",
            UserWarning, stacklevel=2,
        )
    buf = recent_df[cols_needed].copy()
    if O2_DIRECT_COL not in buf.columns:
        buf[O2_DIRECT_COL] = 0.0
    buf, _ = add_derived_features(buf, npr_hinge_threshold=loaded.npr_threshold)
    buf = add_nox_lag_features(buf)
    buf = add_extended_features(buf)
    buf = add_generic_features(buf)
    buf = add_interaction_features(buf)
    buf = add_time_features(buf)

    buf_valid = buf.dropna(subset=FEATURES)

    if len(buf_valid) == 0:
        warnings.warn(
            f"recent_df warm-up 부족(전체 {len(buf)}행, 권장 {MIN_RECENT_ROWS}). "
            "ffill 폴백 — 정확도 저하.",
            UserWarning, stacklevel=2,
        )
        buf_ff = buf.ffill().bfill().fillna(0.0)
        X = buf_ff.iloc[[-1]][FEATURES]
    else:
        if len(buf_valid) < MIN_RECENT_ROWS // 2:
            warnings.warn(
                f"recent_df 유효 행수 부족(유효 {len(buf_valid)}행, 권장 {MIN_RECENT_ROWS}). "
                "마지막 유효 행 사용.",
                UserWarning, stacklevel=2,
            )
        # 마지막 유효 행 = 현재 시점 t 의 피처
        X = buf_valid.iloc[[-1]][FEATURES]

    y_pred = loaded.model.predict(X)
    return float(y_pred[0])


__all__ = ["LoadedForecaster", "load_model", "predict", "MIN_RECENT_ROWS"]
