"""DB sensor_data 테이블 접근 레이어.

DB 컬럼명 ↔ IGCC 태그명 매핑은 운영 환경에서 명시 주입한다.

R5 — 기존 DbContext.session_factory(sessionmaker[Session])는 동기이므로
asyncio thread executor에서 호출하여 async 인터페이스 유지.
"""

import asyncio
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, Session

from app.exceptions import DataSourceUnavailableError
from digital_twin.preprocess import RAW_FEATURES, TARGETS

REQUIRED_TAGS: tuple[str, ...] = tuple(list(RAW_FEATURES) + list(TARGETS))

# 테스트/로컬 전용 fallback. 운영에서는 lifespan이 SENSOR_COLUMN_MAPPING 누락을 차단한다.
TAG_TO_DB_COLUMN: dict[str, str] = {tag: tag for tag in REQUIRED_TAGS}


class SensorRepository:
    def __init__(
        self,
        db_session_factory: sessionmaker[Session],
        tag_to_db_column: dict[str, str] | None = None,
    ):
        """`db_session_factory`: DbContext.session_factory (동기 sessionmaker)."""
        self.session_factory = db_session_factory
        self.tag_to_db_column = (
            TAG_TO_DB_COLUMN if tag_to_db_column is None else tag_to_db_column
        )
        missing = set(REQUIRED_TAGS) - set(self.tag_to_db_column)
        if missing:
            raise DataSourceUnavailableError(
                f"sensor column mapping missing tags: {sorted(missing)}"
            )

    async def fetch_recent_window(self, seconds: int) -> pd.DataFrame:
        """최근 `seconds`초간 데이터 조회. 총 43컬럼 반환 (오래된 → 최신 순)."""
        return await asyncio.to_thread(self._fetch_sync, seconds)

    def _fetch_sync(self, seconds: int) -> pd.DataFrame:
        cols = [self.tag_to_db_column[t] for t in REQUIRED_TAGS]
        col_list = ", ".join(f'"{c}"' for c in cols)
        # R12 — 최신 N행을 DESC LIMIT로 가져온 뒤 ASC로 정렬 (시간 분석용)
        sql = text(
            f"""
            WITH recent AS (
                SELECT measured_at, {col_list}
                FROM sensor_data
                ORDER BY measured_at DESC
                LIMIT :n
            )
            SELECT * FROM recent ORDER BY measured_at ASC
            """
        )
        with self.session_factory() as session:
            result = session.execute(sql, {"n": int(seconds)})
            rows = result.mappings().all()
        df = pd.DataFrame(rows)
        if not df.empty:
            df.rename(
                columns={v: k for k, v in self.tag_to_db_column.items()},
                inplace=True,
            )
            # A3 (5차 보강) — errors="raise". "coerce"는 NaT silent 폴백 위험.
            df["measured_at"] = pd.to_datetime(df["measured_at"], errors="raise")
        return df
