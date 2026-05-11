"""DB 스냅샷 기반 PlantDataSource 구현체 (B안 고정 모드)."""

from datetime import datetime
import pandas as pd

from app.exceptions import DataNotEnoughError
from app.repositories.sensor_repo import SensorRepository


class SnapshotDataSource:
    name = "snapshot"

    def __init__(self, sensor_repo: SensorRepository):
        self.repo = sensor_repo

    async def get_initial_snapshot(self, window_minutes: int = 15) -> pd.DataFrame:
        seconds = window_minutes * 60
        df = await self.repo.fetch_recent_window(seconds=seconds)
        self._validate(df, required_rows=seconds)
        return df

    def poll_latest(self) -> dict[str, float] | None:
        return None  # B안은 미사용

    def get_at_timestamp(self, ts: datetime, window_minutes: int = 15) -> pd.DataFrame:
        raise NotImplementedError("리플레이 모드 미구현 — Phase 2")

    def _validate(self, df: pd.DataFrame, required_rows: int) -> None:
        if len(df) < required_rows:
            raise DataNotEnoughError(
                f"insufficient_data: required {required_rows}, got {len(df)}"
            )
        gaps = df["measured_at"].diff().dt.total_seconds()
        if (gaps > 2.0).any():
            raise DataNotEnoughError("time gap detected in snapshot")
