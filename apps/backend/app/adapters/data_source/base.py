"""플랜트 데이터 공급원 Protocol.

B안 스냅샷·실시간 미러링·리플레이 모드를 통합 추상화.
"""

from datetime import datetime
from typing import Protocol

import pandas as pd


class PlantDataSource(Protocol):
    name: str

    async def get_initial_snapshot(self, window_minutes: int = 15) -> pd.DataFrame:
        """세션 시작 시 1회 호출. 총 43컬럼 시계열 반환."""
        ...

    def poll_latest(self) -> dict[str, float] | None:
        """실시간 모드용. B안 고정 모드는 None."""
        ...

    def get_at_timestamp(self, ts: datetime, window_minutes: int = 15) -> pd.DataFrame:
        """리플레이 모드용. B안은 미구현."""
        ...
