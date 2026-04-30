import pandas as pd
import os
from pathlib import Path
from sqlalchemy import create_engine
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]

TARGET_FOLDER = BASE_DIR / "data" / "raw" / "250811-250825"

load_dotenv()
DB_URL = os.getenv('DATABASE_URL')

if not DB_URL:
    raise ValueError("[에러] DATABASE_URL 환경변수가 없습니다!")

# ==========================================
# 1. 데이터 추출 (Extract)
# ==========================================
print("[Extract] 데이터를 불러오는 중...")
file_list = sorted(TARGET_FOLDER.glob("*.csv"))

if not file_list:
    raise FileNotFoundError(f"[에러] CSV 파일을 찾을 수 없습니다: {TARGET_FOLDER}")

df_list = []
for file in file_list:
    temp_df = pd.read_csv(file, skiprows=[1, 2, 3, 4]) 
    df_list.append(temp_df)

df = pd.concat(df_list, ignore_index=True)

# ==========================================
# 2. 데이터 변환 (Transform) - info.md 기준 컬럼 매핑
# ==========================================
# 결측/불필요 컬럼 제거
df = df.drop(columns=['IGCC.CC.G1.ttfr1', 'Column1'], errors='ignore')

# 💡 info.md 명세서를 바탕으로 프론트/백엔드가 쓰기 편하게 이름 변경
rename_dict = {
    'TagName': 'measured_at',
    'IGCC.DeNOX.AT_H1_901_PV': 'nox_ppm',
    'IGCC.CC.G1.NQKR3_MONITOR': 'dgan_offset',
    'IGCC.CC.G1.ca_fqsg_cl': 'syngas_flow',
    'IGCC.CC.G1.DWATT': 'generator_output',
    'IGCC.CC.G1.VNPR_P': 'npr_primary',
    'IGCC.CC.G1.ATID': 'ambient_temp',
    'IGCC.CC.G1.NQJ': 'dgan_flow',
    'IGCC.CC.G1.csgv': 'igv'
}

missing_columns = [column for column in rename_dict if column not in df.columns]
if missing_columns:
    raise KeyError(f"[에러] 원천 CSV에 필수 컬럼이 없습니다: {missing_columns}")

df = df.rename(columns=rename_dict)
# 날짜가 아닌 이상한 글자(예: 또 다른 파일의 헤더가 섞여있을 경우)가 나오면 에러 내지 말고 NaT로 처리
df['measured_at'] = pd.to_datetime(df['measured_at'], errors='coerce')

# 우리가 지정한 핵심 컬럼 9개만 쏙 뽑아내기
core_columns = list(rename_dict.values())
df_core = df[core_columns].copy()

numeric_columns = [column for column in core_columns if column != 'measured_at']
df_core[numeric_columns] = df_core[numeric_columns].apply(pd.to_numeric, errors='coerce')

# 날짜/센서값 변환 중 생긴 결측 행은 깔끔하게 삭제
df_core = df_core.dropna(subset=core_columns)

print(f"[Transform] 전처리 완료. 총 {len(df_core)}행의 데이터를 DB에 적재합니다...")

# ==========================================
# 3. 데이터 적재 (Load)
# ==========================================
engine = create_engine(DB_URL)

df_core.to_sql(
    name='sensor_data',
    con=engine,
    if_exists='replace',        
    index=False,
    chunksize=10000,
    method='multi'
)

print("[Load] PostgreSQL DB 적재가 끝났습니다.")
