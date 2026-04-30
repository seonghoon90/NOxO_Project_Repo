import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TARGET_FOLDER = BASE_DIR / "data" / "raw" / "250811-250825"
TABLE_NAME = "sensor_data"

COLUMN_MAPPING = {
    "TagName": "measured_at",
    "IGCC.DeNOX.AT_H1_901_PV": "nox_ppm",
    "IGCC.CC.G1.NQKR3_MONITOR": "dgan_offset",
    "IGCC.CC.G1.ca_fqsg_cl": "syngas_flow",
    "IGCC.CC.G1.DWATT": "generator_output",
    "IGCC.CC.G1.VNPR_P": "npr_primary",
    "IGCC.CC.G1.ATID": "ambient_temp",
    "IGCC.CC.G1.NQJ": "dgan_flow",
    "IGCC.CC.G1.csgv": "igv",
}


def get_database_url() -> str:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("[에러] DATABASE_URL 환경변수가 없습니다.")
    return database_url


def extract_sensor_csv(target_folder: Path = DEFAULT_TARGET_FOLDER) -> pd.DataFrame:
    print("[Extract] 데이터를 불러오는 중...")
    file_list = sorted(target_folder.glob("*.csv"))

    if not file_list:
        raise FileNotFoundError(f"[에러] CSV 파일을 찾을 수 없습니다: {target_folder}")

    df_list = [
        pd.read_csv(file, skiprows=[1, 2, 3, 4])
        for file in file_list
    ]
    return pd.concat(df_list, ignore_index=True)


def transform_sensor_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop(columns=["IGCC.CC.G1.ttfr1", "Column1"], errors="ignore")

    missing_columns = [column for column in COLUMN_MAPPING if column not in df.columns]
    if missing_columns:
        raise KeyError(f"[에러] 원천 CSV에 필수 컬럼이 없습니다: {missing_columns}")

    df = df.rename(columns=COLUMN_MAPPING)
    df["measured_at"] = pd.to_datetime(df["measured_at"], errors="coerce")

    core_columns = list(COLUMN_MAPPING.values())
    df_core = df[core_columns].copy()

    numeric_columns = [column for column in core_columns if column != "measured_at"]
    df_core[numeric_columns] = df_core[numeric_columns].apply(pd.to_numeric, errors="coerce")
    df_core = df_core.dropna(subset=core_columns)

    print(f"[Transform] 전처리 완료. 총 {len(df_core)}행의 데이터를 DB에 적재합니다...")
    return df_core


def load_sensor_data(df: pd.DataFrame, database_url: str | None = None) -> None:
    engine = create_engine(database_url or get_database_url())
    df.to_sql(
        name=TABLE_NAME,
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=10000,
        method="multi",
    )
    print("[Load] PostgreSQL DB 적재가 끝났습니다.")


def validate_sensor_data(database_url: str | None = None) -> dict:
    engine = create_engine(database_url or get_database_url())
    query = text(
        f"""
        SELECT
            COUNT(*) AS row_count,
            MIN(measured_at) AS start_at,
            MAX(measured_at) AS end_at,
            SUM(
                CASE
                    WHEN measured_at IS NULL
                        OR nox_ppm IS NULL
                        OR dgan_offset IS NULL
                        OR syngas_flow IS NULL
                        OR generator_output IS NULL
                        OR npr_primary IS NULL
                        OR ambient_temp IS NULL
                        OR dgan_flow IS NULL
                        OR igv IS NULL
                    THEN 1
                    ELSE 0
                END
            ) AS null_row_count
        FROM {TABLE_NAME}
        """
    )

    with engine.connect() as conn:
        row = conn.execute(query).mappings().one()

    result = dict(row)
    if result["row_count"] == 0:
        raise ValueError("[에러] sensor_data 테이블에 적재된 데이터가 없습니다.")
    if result["null_row_count"] > 0:
        raise ValueError(f"[에러] 핵심 컬럼에 결측 행이 있습니다: {result['null_row_count']}")

    print(
        "[Validate] 검증 완료. "
        f"rows={result['row_count']}, "
        f"range={result['start_at']} ~ {result['end_at']}"
    )
    return result


def run_pipeline() -> dict:
    database_url = get_database_url()
    raw_df = extract_sensor_csv()
    sensor_df = transform_sensor_data(raw_df)
    load_sensor_data(sensor_df, database_url)
    return validate_sensor_data(database_url)


if __name__ == "__main__":
    run_pipeline()
