"""
digital_twin/preprocess.py
===========================
피처/타깃 정의 및 데이터 전처리.

피처 설계 근거 (analysis/hypothesis/ 검증 결과)
-----------------------------------------------
- H1: IGCC.DeNOX.AIT_H1_902 (O2) 제외 — 준누수 확인 (O2 단독 R²=0.9948)
- H2: 통합 모델 유지 — 구간 분리 불필요 (GLOBAL_BETTER)
- H3: NQJ lag 피처 추가 — 다변수 맥락에서 인과 방향 반영
- H4: TTXM lag/rolling 피처 추가 — 열관성 지연 보완
- H5: NPR 파생·상호작용 피처 추가 — 비선형성·상호작용 효과 확인
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

# ── 원시 센서 피처 (39개, O2 제외) ─────────────────────────────────────────
RAW_FEATURES = [
    "IGCC.CC.G1.FPSG",
    "IGCC.CC.G1.FTSG",
    "IGCC.CC.G1.ca_fqsg_cl",
    "IGCC.CC.G1.LHVSYNDW_SCF",
    "IGCC.CC.G1.FSAGR",
    "IGCC.CC.G1.FPSG2",
    "IGCC.CC.G1.FSAG11A",
    "IGCC.CC.G1.FSAG11",
    "IGCC.CC.G1.FSAG12",
    "IGCC.CC.G1.FPSG3",
    "IGCC.CC.G1.AFDPM",
    "IGCC.CC.G1.CTIM",
    "IGCC.CC.G1.afpap",
    "IGCC.CC.G1.csgv",
    "IGCC.CC.G1.CPD",
    "IGCC.CC.G1.CTD",
    "IGCC.CC.G1.CSBHX",
    "IGCC.CC.G1.tnh_v",
    "IGCC.CC.G1.ATID",
    "IGCC.CC.G1.EXHMASS",
    "IGCC.CC.G1.FPGN1_SEL",
    "IGCC.CC.G1.FPGN2_SEL",
    "IGCC.CC.G1.ROUTPUT_32",
    "IGCC.CC.G1.VNPR_S",
    "IGCC.CC.G1.VNPR_P",
    "IGCC.CC.G1.NPNJ",
    "IGCC.CC.G1.NTNJ",
    "IGCC.CC.G1.NQJ",
    "IGCC.CC.G1.NQJO2",
    "IGCC.CC.G1.nicvs1",
    "IGCC.CC.G1.ndt1",
    "IGCC.CC.G1.NPNJ2",
    "IGCC.CC.G1.NQKR3_MONITOR",
    "IGCC.CC.G1.ROUTPUT_6",
    "IGCC.IG.PIC7069A.PV",
    "IGCC.IG.ZT7069B.PV",
    # "IGCC.DeNOX.AIT_H1_902",  # H1: 준누수 제외 (O2 단독 R²=0.9948)
    "IGCC.DeNOX.TT_H1_90123",
    "IGCC.CC.G1.itdp",
    "IGCC.CC.G1.tcsph1",
]

# ── 파생 피처 이름 목록 ─────────────────────────────────────────────────────
# H5: NPR 파생 (즉시 계산 — 이전 데이터 불필요)
_H5_FEATURES = [
    "feat_NPR_avg",      # (VNPR_P + VNPR_S) / 2
    "feat_NPR_gap",      # VNPR_P - VNPR_S
    "feat_NPR_hinge",    # max(0, NPR_avg - 학습 중간값)
    "feat_NPR_x_NQJ",    # NPR_avg × NQJ
]

# H3: NQJ lag (1초 간격 기준, 1분=60행)
_H3_FEATURES = [
    "feat_NQJ_lag_1min",
    "feat_NQJ_lag_3min",
    "feat_NQJ_lag_5min",
]

# H4: TTXM lag/rolling (1분 lag, 5분·15분 이동평균)
_H4_FEATURES = [
    "feat_TTXM_lag_1min",
    "feat_TTXM_roll_5min",
    "feat_TTXM_roll_15min",
]

DERIVED_FEATURES = _H5_FEATURES + _H3_FEATURES + _H4_FEATURES

# ── 모델이 사용하는 전체 피처 목록 ─────────────────────────────────────────
FEATURES = RAW_FEATURES + DERIVED_FEATURES   # 39 + 10 = 49개

# ── 타깃 ────────────────────────────────────────────────────────────────────
TARGETS = [
    "IGCC.DeNOX.AT_H1_901_PV",   # NOx [ppm]
    "IGCC.CC.G1.DWATT",           # 발전량 [MW]
    "IGCC.CC.G1.TTXM",            # 배기가스온도 [°C]
]

# NPR hinge 임계값 — train.py 에서 학습 데이터 중간값으로 설정, metadata에 저장
NPR_HINGE_THRESHOLD: float | None = None


# ── 파생 피처 계산 ───────────────────────────────────────────────────────────

def add_derived_features(
    df: pd.DataFrame,
    npr_hinge_threshold: float | None = None,
) -> pd.DataFrame:
    """파생 피처를 df에 추가해 반환.

    Parameters
    ----------
    df:
        RAW_FEATURES + TARGETS 컬럼이 포함된 DataFrame.
        1초 간격 시계열 순서를 유지해야 lag/rolling 계산이 정확함.
    npr_hinge_threshold:
        NPR_hinge = max(0, NPR_avg - threshold).
        None이면 df의 NPR_avg 중간값 사용 (학습 시).
        추론 시에는 반드시 학습 중 계산한 값(metadata에 저장된 값)을 넣어야 함.

    Returns
    -------
    pd.DataFrame
        파생 피처가 추가된 복사본.
    """
    df = df.copy()

    # H5: NPR 파생 ─────────────────────────────────────────────────
    vnpr_s = df["IGCC.CC.G1.VNPR_S"]
    vnpr_p = df["IGCC.CC.G1.VNPR_P"]
    nqj    = df["IGCC.CC.G1.NQJ"]

    df["feat_NPR_avg"] = (vnpr_p + vnpr_s) / 2
    df["feat_NPR_gap"] = vnpr_p - vnpr_s

    if npr_hinge_threshold is None:
        npr_hinge_threshold = float(df["feat_NPR_avg"].median())

    df["feat_NPR_hinge"] = np.maximum(0.0, df["feat_NPR_avg"] - npr_hinge_threshold)
    df["feat_NPR_x_NQJ"] = df["feat_NPR_avg"] * nqj

    # H3: NQJ lag ──────────────────────────────────────────────────
    df["feat_NQJ_lag_1min"] = nqj.shift(60)
    df["feat_NQJ_lag_3min"] = nqj.shift(180)
    df["feat_NQJ_lag_5min"] = nqj.shift(300)

    # H4: TTXM lag/rolling ─────────────────────────────────────────
    ttxm = df["IGCC.CC.G1.TTXM"]
    df["feat_TTXM_lag_1min"]   = ttxm.shift(60)
    df["feat_TTXM_roll_5min"]  = ttxm.rolling(300,  min_periods=150).mean()
    df["feat_TTXM_roll_15min"] = ttxm.rolling(900,  min_periods=450).mean()

    return df, npr_hinge_threshold


# ── 데이터 로딩 ─────────────────────────────────────────────────────────────

def load_data(
    path: str | Path,
    npr_hinge_threshold: float | None = None,
) -> tuple[pd.DataFrame, float]:
    """CSV를 읽어 파생 피처까지 추가한 DataFrame 반환.

    Returns
    -------
    (df, npr_hinge_threshold)
        df: FEATURES + TARGETS 컬럼.
        npr_hinge_threshold: 이번 호출에서 사용된 NPR hinge 기준값.
    """
    df = pd.read_csv(
        path,
        header=0,
        skiprows=[1, 2, 3, 4],
        index_col=0,
        encoding="utf-8-sig",
    )

    # 원시 피처 + 타깃 컬럼 유효성 검사
    missing = set(RAW_FEATURES + TARGETS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {Path(path).name}: {sorted(missing)}")

    df = df[RAW_FEATURES + TARGETS]
    df = df.apply(pd.to_numeric, errors="coerce")

    # 파생 피처 추가 (lag/rolling → NaN 발생)
    df, npr_hinge_threshold = add_derived_features(df, npr_hinge_threshold)

    before = len(df)
    df = df.dropna(subset=FEATURES + TARGETS)
    dropped = before - len(df)
    if dropped > 0:
        print(
            f"[load_data] Dropped {dropped} rows ({dropped/before:.1%}) "
            f"(lag warm-up + NaN) from {Path(path).name}"
        )

    return df, npr_hinge_threshold


def aggregate_to_1min(df: pd.DataFrame) -> pd.DataFrame:
    """1초 단위 시계열을 1분(60행) 평균으로 집계.

    근거: 1초 데이터의 자기상관(NOx lag=1s: 0.989)으로 인해 LightGBM이
    학습 분포에 과적합. 1분 집계는 다음을 동시에 달성:
      - 센서 노이즈 제거 (열역학적 시정수와 정합)
      - 분포 이동(train/test) 영향 완화
      - NOx R² 0.4707 → 0.6030 (+28%)
    """
    if len(df) < 60:
        raise ValueError(f"1분 집계에는 최소 60행 필요. 입력: {len(df)}행")
    n_rows = len(df) // 60 * 60
    df_cut = df.iloc[:n_rows].copy()
    group = np.arange(n_rows) // 60
    return df_cut.groupby(group).mean()


def split_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    return df[FEATURES], df[TARGETS]


def train_val_split(
    df: pd.DataFrame, val_ratio: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0 < val_ratio < 1:
        raise ValueError(f"val_ratio must be between 0 and 1, got {val_ratio}")
    split_idx = int(len(df) * (1 - val_ratio))
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()
