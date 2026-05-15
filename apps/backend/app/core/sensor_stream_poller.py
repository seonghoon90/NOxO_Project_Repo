"""SensorStreamRepository → SensorBuffer 폴링 어댑터.

KafkaSensorStream의 DB 버전. Kafka consumer 대신 (ingested_at, id) composite
cursor 기반 폴링으로 stream row를 SensorBuffer에 주입한다.

상호배타 — KafkaSensorStream과 동시 활성화 금지(둘 다 buffer.append → 중복).
lifespan에서 KAFKA_STREAM_ENABLED ↔ SENSOR_STREAM_POLL_ENABLED 가드.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from app.core.sensor_buffer import SensorBuffer
from app.repositories.sensor_stream_repo import (
    SensorStreamRepository,
    StreamCursor,
)

logger = logging.getLogger(__name__)

# DB 폴링 실패 임계 — 5회 연속 실패 시 down 판정 + ERROR 로그.
_FAILURE_THRESHOLD = 5
# down 지속 시 ERROR 재발신 간격(tick 수) — 운영 알림이 1줄에 묻히지 않게 한다.
# 폴링 간격 1초 가정 시 약 1분에 한 번.
_DOWN_ERROR_REPEAT_INTERVAL = 60


def _to_iso_measured_at(value: Any) -> Any:
    """datetime → UTC ISO 문자열(Z suffix). KafkaSensorStream 경로와 키 호환.

    RealtimeEngine `_build_payload`가 `isinstance(kafka_ts, str)` 검사로 분기 →
    datetime 객체 그대로 두면 wall-clock 폴백된다. 문자열 입력은 그대로 통과.
    """
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return value


class SensorStreamPoller:
    """sensor_data_stream을 주기 폴링해 SensorBuffer에 append."""

    def __init__(
        self,
        repo: SensorStreamRepository,
        sensor_buffer: SensorBuffer,
        *,
        poll_interval_sec: float = 1.0,
        fetch_limit: int = 200,
    ) -> None:
        self._repo = repo
        self._buffer = sensor_buffer
        self._poll_interval = poll_interval_sec
        self._fetch_limit = fetch_limit
        self._last_seen: StreamCursor | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None
        self._consecutive_failures = 0
        self._down = False
        self._last_error: str | None = None

    @property
    def last_seen(self) -> StreamCursor | None:
        return self._last_seen

    @property
    def is_down(self) -> bool:
        return self._down

    @property
    def last_error(self) -> str | None:
        return self._last_error

    async def start(self) -> None:
        """초기 cursor를 latest_cursor로 설정 후 폴링 루프 시작.

        latest 조회 실패 시 cursor=None으로 시작하면 전체 테이블 재처리 위험 →
        시작 자체를 down 상태로 진입하고 매 tick 자기 치유(latest 재조회).
        """
        if self._task is not None:
            return
        try:
            self._last_seen = await self._repo.latest_cursor()
        except Exception as exc:
            logger.error("sensor_stream_poll_init_failed err=%s", exc)
            self._last_error = repr(exc)
            self._consecutive_failures = _FAILURE_THRESHOLD
            self._down = True
        logger.info(
            "sensor_stream_poller_started last_seen=%s interval=%.2fs",
            self._last_seen, self._poll_interval,
        )
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="sensor_stream_poller")

    async def stop(self) -> None:
        if self._task is None:
            return
        assert self._stop_event is not None
        self._stop_event.set()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        self._stop_event = None
        logger.info("sensor_stream_poller_stopped")

    async def _run(self) -> None:
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            await self._tick_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._poll_interval,
                )
            except asyncio.TimeoutError:
                pass

    async def _tick_once(self) -> None:
        try:
            await self._fetch_and_append()
        except Exception as exc:
            self._record_failure(exc)
            return
        self._record_success()

    async def _fetch_and_append(self) -> None:
        # cursor 미설정(start init 실패 또는 빈 테이블) → latest 재조회로 복구 시도.
        if self._last_seen is None:
            self._last_seen = await self._repo.latest_cursor()
            if self._last_seen is None:
                return
        rows = await self._repo.fetch_since(self._last_seen, limit=self._fetch_limit)
        if not rows:
            return
        for row in rows:
            self._buffer.append(self._to_buffer_row(row))
        # 마지막 row의 (ingested_at, id)로 cursor 전진(ASC 정렬 보장).
        last = rows[-1]
        self._last_seen = (last["ingested_at"], int(last["id"]))

    @staticmethod
    def _to_buffer_row(row: dict[str, Any]) -> dict[str, Any]:
        # SensorBuffer는 도메인 키만 기대 — lineage 컬럼(ingested_at·id) strip,
        # measured_at은 ISO 문자열로 정규화해 KafkaSensorStream 경로와 호환.
        out = {k: v for k, v in row.items() if k not in ("ingested_at", "id")}
        if "measured_at" in out:
            out["measured_at"] = _to_iso_measured_at(out["measured_at"])
        return out

    def _record_success(self) -> None:
        if self._down:
            logger.info("sensor_stream_poll_recovered last_seen=%s", self._last_seen)
        self._consecutive_failures = 0
        self._down = False
        self._last_error = None

    def _record_failure(self, exc: BaseException) -> None:
        self._consecutive_failures += 1
        self._last_error = repr(exc)
        if not self._down and self._consecutive_failures >= _FAILURE_THRESHOLD:
            self._down = True
            logger.error(
                "sensor_stream_poll_db_down failures=%d err=%s",
                self._consecutive_failures, exc,
            )
        elif self._down and self._consecutive_failures % _DOWN_ERROR_REPEAT_INTERVAL == 0:
            # 알림 채널 noise filter에 묻히지 않도록 down 지속 시 주기적 ERROR.
            logger.error(
                "sensor_stream_poll_still_down failures=%d err=%s",
                self._consecutive_failures, exc,
            )
        else:
            logger.warning(
                "sensor_stream_poll_failed n=%d err=%s",
                self._consecutive_failures, exc,
            )
