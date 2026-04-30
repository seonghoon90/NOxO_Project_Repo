import pandas as pd
from pathlib import Path

FEATURES = [
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
    "IGCC.DeNOX.AIT_H1_902",
    "IGCC.DeNOX.TT_H1_90123",
    "IGCC.CC.G1.itdp",
    "IGCC.CC.G1.tcsph1",
]

TARGETS = [
    "IGCC.DeNOX.AT_H1_901_PV",
    "IGCC.CC.G1.DWATT",
    "IGCC.CC.G1.TTXM",
]


def load_data(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        header=0,
        skiprows=[1, 2, 3, 4],
        index_col=0,
        encoding="utf-8-sig",
    )
    missing = set(FEATURES + TARGETS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {Path(path).name}: {sorted(missing)}")
    df = df[FEATURES + TARGETS]
    df = df.apply(pd.to_numeric, errors="coerce")
    before = len(df)
    df = df.dropna()
    dropped = before - len(df)
    if dropped > 0:
        print(f"[load_data] Dropped {dropped} rows ({dropped/before:.1%}) with non-numeric values from {Path(path).name}")
    return df


def split_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    return df[FEATURES], df[TARGETS]


def train_val_split(
    df: pd.DataFrame, val_ratio: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0 < val_ratio < 1:
        raise ValueError(f"val_ratio must be between 0 and 1, got {val_ratio}")
    split_idx = int(len(df) * (1 - val_ratio))
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()
