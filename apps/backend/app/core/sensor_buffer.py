"""Sensor data sliding window buffer (전역 singleton).

bootstrap (CSV/DB 15분) + Kafka stream을 단일 deque에 합친다.
DT 모델 입력의 외란 source 역할 (세션별 입력은 SessionContext.recent_df_buffer).
"""

from __future__ import annotations

from collections import deque
from typing import Any

import pandas as pd


class SensorBuffer:
    """1초 tick 센서 데이터의 sliding window (maxlen 행)."""

    def __init__(self, maxlen: int = 900) -> None:
        self._buffer: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def load_bootstrap(self, rows: list[dict[str, Any]]) -> None:
        """startup 시 1회 호출. 기존 내용 모두 비우고 rows를 채운다.

        rows는 normalize_raw_message로 변환된 도메인 snake_case dict 리스트.
        """
        self._buffer.clear()
        self._buffer.extend(rows)

    def append(self, row: dict[str, Any]) -> None:
        """Kafka consumer가 새 메시지 도착 시 호출. maxlen 초과 시 oldest evict."""
        self._buffer.append(row)

    def latest_row(self) -> dict[str, Any] | None:
        """가장 최근 1행 반환. 비어있으면 None."""
        if not self._buffer:
            return None
        return self._buffer[-1]

    def to_dataframe(self) -> pd.DataFrame:
        """전체 buffer → DataFrame. SessionContext 초기화 시 사용."""
        return pd.DataFrame(list(self._buffer))

    def __len__(self) -> int:
        return len(self._buffer)
