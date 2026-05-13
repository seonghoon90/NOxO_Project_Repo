"""5분 NOx 예측용 피처/타깃 생성 파이프라인 (v2: 1초 단위 + NOx lag).

v2 변경 사항 (Forecast01 분석 결과 반영):
- 1분 집계 폐기 → 1초 단위 학습 (자기상관은 NOx 자체 lag 피처로 해소)
- NOx lag/rolling 피처 추가 — Forecast01 feature importance 1·4·5위
- shift(-300) 1초 단위 타깃 (5분 = 300초)
- subsample 옵션 (학습 속도/메모리)

기존 `digital_twin.preprocess`의 피처 엔지니어링은 도메인 지식이므로 import 재사용.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pathlib import Path

from digital_twin.preprocess import (
    FEATURES as _DT_FEATURES,
    RAW_FEATURES as _DT_RAW_FEATURES,
    add_derived_features,
    load_data as _dt_load_data,
)

# v2.7: O2 피처 포함 (5분 horizon에서는 누수 아님)
# - O2(t)로 NOx(t+300s) 예측 → 미래 정보 사용 아니므로 엄밀한 ML 누수 아님
# - 화학적 동시성(O2↔NOx R²=0.99)은 t+0 시점 우려이지 5분 horizon에선 약화
# - holdout 실측 결과 O2 포함 시 R² +0.046 개선 (0.636→0.683)
# - NQJO2 + 직접 O2(AIT_H1_902) 모두 사용
O2_DIRECT_COL: str = "IGCC.DeNOX.AIT_H1_902"
NQJO2_COL: str = "IGCC.CC.G1.NQJO2"

# 직접 O2 센서를 RAW_FEATURES에 강제 추가 (기존 digital_twin.preprocess가 제외했음)
RAW_FEATURES: list[str] = list(_DT_RAW_FEATURES)
if O2_DIRECT_COL not in RAW_FEATURES:
    RAW_FEATURES.append(O2_DIRECT_COL)
BASE_FEATURES: list[str] = list(_DT_FEATURES)
if O2_DIRECT_COL not in BASE_FEATURES:
    BASE_FEATURES.append(O2_DIRECT_COL)

NOX_TARGET_COL: str = "IGCC.DeNOX.AT_H1_901_PV"
FORECAST_HORIZON_SEC: int = 300  # 1초 단위 학습 — 5분 = 300초
FORECAST_HORIZON_MIN: int = 5  # 호환성 유지 (외부 참조용)
TARGET_COL: str = "target_nox_5min"

# Forecast01 feature importance + 추가 NOx lag/diff/rolling (v2.3 확장)
# 1·4·5위 + 다중 시간 스케일 (1s/5s/10s/30s/60s/120s/180s/240s/300s)
NOX_LAG_FEATURES: list[str] = (
    [f"nox_lag_{s}s" for s in [1, 5, 10, 30, 60, 120, 180, 240, 300]]
    + [f"nox_roll_mean_{s}s" for s in [10, 30, 60, 120, 180, 300]]
    + [f"nox_roll_std_{s}s" for s in [10, 30, 120, 180, 300]]
    + [f"nox_diff_{s}s" for s in [10, 60, 120, 180, 300]]
)

# Forecast01 feature importance 상위 다른 핵심 피처들 (운전/압력/유량 diff·rolling·lag)
# 패턴별 변수 매핑:
#   diff_60s   : CPD, DWATT
#   diff_180s  : FPSG, CPD
#   diff_300s  : CPD
#   roll_mean_180s: VNPR_S
#   roll_mean_300s: FPSG, VNPR_P
#   roll_mean_900s: NQJ, CPD, NTNJ, VNPR_S, VNPR_P, ca_fqsg_cl
#   lag_180s   : FPSG, CPD, LHVSYNDW_SCF
_DIFF_FEATURE_SPECS: list[tuple[str, int]] = [
    ("IGCC.CC.G1.CPD", 60),
    ("IGCC.CC.G1.DWATT", 60),
    ("IGCC.CC.G1.FPSG", 180),
    ("IGCC.CC.G1.CPD", 180),
    ("IGCC.CC.G1.CPD", 300),
]
_ROLL_FEATURE_SPECS: list[tuple[str, int]] = [
    ("IGCC.CC.G1.VNPR_S", 180),
    ("IGCC.CC.G1.FPSG", 300),
    ("IGCC.CC.G1.VNPR_P", 300),
    ("IGCC.CC.G1.NQJ", 900),
    ("IGCC.CC.G1.CPD", 900),
    ("IGCC.CC.G1.NTNJ", 900),
    ("IGCC.CC.G1.VNPR_S", 900),
    ("IGCC.CC.G1.VNPR_P", 900),
    ("IGCC.CC.G1.ca_fqsg_cl", 900),
]
_LAG_FEATURE_SPECS: list[tuple[str, int]] = [
    ("IGCC.CC.G1.FPSG", 180),
    ("IGCC.CC.G1.CPD", 180),
    ("IGCC.CC.G1.LHVSYNDW_SCF", 180),
]


def _short_name(col: str) -> str:
    """피처 이름에서 접두사 제거 (IGCC.CC.G1. → '')."""
    return col.replace("IGCC.CC.G1.", "")


EXT_DIFF_FEATURES: list[str] = [f"{_short_name(c)}_diff_{w}s" for c, w in _DIFF_FEATURE_SPECS]
EXT_ROLL_FEATURES: list[str] = [f"{_short_name(c)}_roll_mean_{w}s" for c, w in _ROLL_FEATURE_SPECS]
EXT_LAG_FEATURES: list[str] = [f"{_short_name(c)}_lag_{w}s" for c, w in _LAG_FEATURE_SPECS]
EXTENDED_FEATURES: list[str] = EXT_DIFF_FEATURES + EXT_ROLL_FEATURES + EXT_LAG_FEATURES

# v2.4 상호작용 피처 (NOx × 운전 변수)
INTERACTION_FEATURES: list[str] = [
    "nox_x_FPSG", "nox_x_CPD", "nox_x_NQJ", "nox_x_VNPR_S",
    "noxdiff60_x_FPSGdiff180", "noxdiff300_x_CPDdiff300",
]

# v2.4 시간 피처 (시각 cyclic encoding)
TIME_FEATURES: list[str] = ["hour_sin", "hour_cos", "minute_of_hour"]

# v2.5 일반화 피처 — 핵심 운전 변수 15개에 lag/diff/roll 자동 생성
_GENERIC_KEY_VARS: list[str] = [
    "IGCC.CC.G1.FPSG", "IGCC.CC.G1.CPD", "IGCC.CC.G1.NQJ", "IGCC.CC.G1.NTNJ",
    "IGCC.CC.G1.VNPR_S", "IGCC.CC.G1.VNPR_P",
    "IGCC.CC.G1.NQJO2",  # v2.7: O2 포함 (5분 horizon에서 누수 아님)
    "IGCC.CC.G1.itdp", "IGCC.CC.G1.afpap", "IGCC.CC.G1.ATID",
    "IGCC.CC.G1.CTIM", "IGCC.CC.G1.CSBHX", "IGCC.CC.G1.ca_fqsg_cl",
    "IGCC.CC.G1.LHVSYNDW_SCF", "IGCC.DeNOX.TT_H1_90123",
    O2_DIRECT_COL,  # v2.7: 직접 O2 센서
]
_GENERIC_LAG_DIFF_SECS = [60, 300]
_GENERIC_ROLL_SECS = [60, 300, 900]


def _generic_short(col: str) -> str:
    return col.replace("IGCC.CC.G1.", "").replace("IGCC.DeNOX.", "")


GENERIC_FEATURES: list[str] = []
for _c in _GENERIC_KEY_VARS:
    _short = _generic_short(_c)
    for _s in _GENERIC_LAG_DIFF_SECS:
        GENERIC_FEATURES.append(f"{_short}_lag_{_s}s_g")
        GENERIC_FEATURES.append(f"{_short}_diff_{_s}s_g")
    for _s in _GENERIC_ROLL_SECS:
        GENERIC_FEATURES.append(f"{_short}_roll_{_s}s_g")

# 전체 피처: 49(base) + 25(nox lag) + 17(extended) + 6(interaction) + 3(time) + 105(generic) = 205
FEATURES: list[str] = (
    BASE_FEATURES + NOX_LAG_FEATURES + EXTENDED_FEATURES
    + INTERACTION_FEATURES + TIME_FEATURES + GENERIC_FEATURES
)


def load_data(csv_path, npr_hinge_threshold: float | None = None):
    """digital_twin.preprocess.load_data + 직접 O2 센서(AIT_H1_902) 합치기.

    기존 load_data는 RAW_FEATURES + TARGETS 컬럼만 유지하므로 AIT_H1_902가
    탈락한다. 5분 horizon에선 O2 포함이 정당하므로 raw CSV에서 직접 읽어 합친다.
    """
    df, npr = _dt_load_data(csv_path, npr_hinge_threshold=npr_hinge_threshold)
    if O2_DIRECT_COL not in df.columns:
        try:
            raw = pd.read_csv(
                csv_path, header=0, skiprows=[1, 2, 3, 4],
                index_col=0, encoding="utf-8-sig",
                usecols=lambda c: c == "TagName" or c == O2_DIRECT_COL,
            )
            df[O2_DIRECT_COL] = pd.to_numeric(
                raw[O2_DIRECT_COL].reindex(df.index), errors="coerce"
            )
        except Exception:
            # O2 컬럼 없으면 0으로 폴백 (모델은 학습 시 분포 학습)
            df[O2_DIRECT_COL] = 0.0
    return df, npr


def add_nox_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """1초 시계열에 NOx lag/rolling/diff 피처 대량 추가 (v2.3)."""
    if NOX_TARGET_COL not in df.columns:
        raise ValueError(f"입력에 {NOX_TARGET_COL} 컬럼이 필요합니다.")
    out = df.copy()
    nox = out[NOX_TARGET_COL]
    # 다중 lag (현재 ~ 5분 전)
    for sec in [1, 5, 10, 30, 60, 120, 180, 240, 300]:
        out[f"nox_lag_{sec}s"] = nox.shift(sec)
    # 다중 rolling mean / std (단기·중기·장기)
    for sec in [10, 30, 60, 120, 180, 300]:
        out[f"nox_roll_mean_{sec}s"] = nox.rolling(sec, min_periods=max(1, sec // 3)).mean()
    for sec in [10, 30, 120, 180, 300]:
        out[f"nox_roll_std_{sec}s"] = nox.rolling(sec, min_periods=max(2, sec // 3)).std()
    # 다중 diff (트렌드)
    for sec in [10, 60, 120, 180, 300]:
        out[f"nox_diff_{sec}s"] = nox.diff(sec)
    return out


def add_extended_features(df: pd.DataFrame) -> pd.DataFrame:
    """Forecast01 feature importance 상위 피처 추가 (diff/roll/lag).

    df는 _DIFF/ROLL/LAG_FEATURE_SPECS에 나오는 원본 컬럼들을 포함해야 함.
    """
    out = df.copy()

    for col, window in _DIFF_FEATURE_SPECS:
        if col not in out.columns:
            raise ValueError(f"확장 피처용 컬럼 누락: {col}")
        feat_name = f"{_short_name(col)}_diff_{window}s"
        out[feat_name] = out[col].diff(window)

    for col, window in _ROLL_FEATURE_SPECS:
        if col not in out.columns:
            raise ValueError(f"확장 피처용 컬럼 누락: {col}")
        feat_name = f"{_short_name(col)}_roll_mean_{window}s"
        # min_periods=window//3 → warmup 영역 축소
        out[feat_name] = out[col].rolling(window, min_periods=window // 3).mean()

    for col, window in _LAG_FEATURE_SPECS:
        if col not in out.columns:
            raise ValueError(f"확장 피처용 컬럼 누락: {col}")
        feat_name = f"{_short_name(col)}_lag_{window}s"
        out[feat_name] = out[col].shift(window)

    return out


def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """v2.4 상호작용 피처: NOx × 운전 변수."""
    out = df.copy()
    nox = out[NOX_TARGET_COL]
    out["nox_x_FPSG"]   = nox * out["IGCC.CC.G1.FPSG"]
    out["nox_x_CPD"]    = nox * out["IGCC.CC.G1.CPD"]
    out["nox_x_NQJ"]    = nox * out["IGCC.CC.G1.NQJ"]
    out["nox_x_VNPR_S"] = nox * out["IGCC.CC.G1.VNPR_S"]
    # diff × diff (변화율 곱)
    if "nox_diff_60s" in out.columns and "FPSG_diff_180s" in out.columns:
        out["noxdiff60_x_FPSGdiff180"] = out["nox_diff_60s"] * out["FPSG_diff_180s"]
    if "nox_diff_300s" in out.columns and "CPD_diff_300s" in out.columns:
        out["noxdiff300_x_CPDdiff300"] = out["nox_diff_300s"] * out["CPD_diff_300s"]
    return out


def add_generic_features(df: pd.DataFrame) -> pd.DataFrame:
    """v2.5 일반화 피처: 핵심 운전 변수 15개에 lag/diff/roll 자동 적용."""
    out = df.copy()
    for col in _GENERIC_KEY_VARS:
        if col not in out.columns:
            continue
        s = out[col]
        short = _generic_short(col)
        for sec in _GENERIC_LAG_DIFF_SECS:
            out[f"{short}_lag_{sec}s_g"] = s.shift(sec)
            out[f"{short}_diff_{sec}s_g"] = s.diff(sec)
        for sec in _GENERIC_ROLL_SECS:
            out[f"{short}_roll_{sec}s_g"] = s.rolling(sec, min_periods=max(1, sec // 3)).mean()
    return out


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """v2.4 시간 피처: 시각 cyclic encoding.

    df.index가 datetime parsable해야 함 (CSV의 timestamp 컬럼).
    실패 시 0으로 폴백 (학습/추론 모두 안전).
    """
    out = df.copy()
    try:
        ts = pd.to_datetime(out.index, errors="coerce")
        hour = ts.hour.astype(float).fillna(0)
        minute = ts.minute.astype(float).fillna(0)
        out["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        out["hour_cos"] = np.cos(2 * np.pi * hour / 24)
        out["minute_of_hour"] = minute
    except Exception:
        out["hour_sin"] = 0.0
        out["hour_cos"] = 0.0
        out["minute_of_hour"] = 0.0
    return out


def make_forecast_target_1s(df_1s: pd.DataFrame) -> pd.DataFrame:
    """1초 단위 DataFrame에 5분 뒤(300초 뒤) NOx 타깃 추가."""
    if NOX_TARGET_COL not in df_1s.columns:
        raise ValueError(f"입력에 {NOX_TARGET_COL} 컬럼이 필요합니다.")
    out = df_1s.copy()
    out[TARGET_COL] = out[NOX_TARGET_COL].shift(-FORECAST_HORIZON_SEC)
    out = out.dropna(subset=[TARGET_COL]).reset_index(drop=True)
    return out


def build_training_dataset(
    csv_path,
    npr_hinge_threshold: float | None = None,
    subsample_sec: int = 5,
) -> tuple[pd.DataFrame, pd.Series, dict]:
    """CSV → 1초 단위 + NOx lag + 300초 shift → (X, y, metadata).

    subsample_sec: 자기상관 완화용 등간격 subsample (기본 5초).
                   1로 하면 모든 1초 샘플 사용.
    """
    df_1s, npr_threshold = load_data(csv_path, npr_hinge_threshold=npr_hinge_threshold)
    df_1s = add_nox_lag_features(df_1s)
    df_1s = add_extended_features(df_1s)
    df_1s = add_generic_features(df_1s)
    df_1s = add_interaction_features(df_1s)
    df_1s = add_time_features(df_1s)
    df_1s = df_1s.dropna(subset=NOX_LAG_FEATURES + EXTENDED_FEATURES + GENERIC_FEATURES)  # warmup

    df_target = make_forecast_target_1s(df_1s)

    # subsample (자기상관 완화 + 학습 속도)
    if subsample_sec > 1:
        df_target = df_target.iloc[::subsample_sec].reset_index(drop=True)

    X = df_target[FEATURES].copy()
    y = df_target[TARGET_COL].copy()
    metadata = {
        "npr_hinge_threshold": float(npr_threshold),
        "n_samples": int(len(X)),
        "subsample_sec": int(subsample_sec),
        "resolution": "1s",
    }
    return X, y, metadata


__all__ = [
    "NOX_TARGET_COL",
    "FORECAST_HORIZON_SEC",
    "FORECAST_HORIZON_MIN",
    "TARGET_COL",
    "FEATURES",
    "BASE_FEATURES",
    "RAW_FEATURES",
    "NOX_LAG_FEATURES",
    "EXTENDED_FEATURES",
    "INTERACTION_FEATURES",
    "TIME_FEATURES",
    "GENERIC_FEATURES",
    "add_derived_features",
    "add_nox_lag_features",
    "add_extended_features",
    "add_interaction_features",
    "add_time_features",
    "add_generic_features",
    "load_data",
    "make_forecast_target_1s",
    "build_training_dataset",
]
