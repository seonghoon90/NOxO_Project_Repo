"""SensorStreamPoller — SensorStreamRepository → SensorBuffer 주입 검증."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.sensor_buffer import SensorBuffer
from app.core.sensor_stream_poller import SensorStreamPoller


def _row(row_id: int, ingested_at: datetime, nox: float = 30.0) -> dict:
    """repo._to_domain_dict가 반환하는 형태(도메인 키 + lineage 보존)."""
    return {
        "syngas_flow": 100.0, "igv_opening": 80.0, "n2_offset": 5.0,
        "n2_valve_1": 42.0, "syngas_srv": 60.0, "syngas_gcv_1": 55.0,
        "syngas_gcv_1a": 54.0, "syngas_gcv_2": 53.0, "ibh_valve": 30.0,
        "n2_flow": 25.0, "nox": nox, "exhaust_temp": 580.0,
        "power": 165.0, "vnpr_p": 1.5,
        "measured_at": ingested_at, "ingested_at": ingested_at, "id": row_id,
    }


def _make_poller(
    fetch_rows: list[dict] | Exception,
    initial_latest: tuple | None = (datetime(2026, 5, 15, 10, 0, 0), 0),
) -> tuple[SensorStreamPoller, SensorBuffer, AsyncMock]:
    repo = AsyncMock()
    repo.latest_cursor.return_value = initial_latest
    if isinstance(fetch_rows, Exception):
        repo.fetch_since.side_effect = fetch_rows
    else:
        repo.fetch_since.return_value = fetch_rows
    buf = SensorBuffer(maxlen=900)
    poller = SensorStreamPoller(repo, buf, poll_interval_sec=0.01)
    return poller, buf, repo


@pytest.mark.asyncio
async def test_tick_appends_rows_to_buffer_with_domain_keys():
    """fetch_since 결과가 lineage strip 후 SensorBuffer.append 된다."""
    base = datetime(2026, 5, 15, 10, 0, 1, tzinfo=timezone.utc)
    rows = [_row(i + 1, base + timedelta(seconds=i), nox=30.0 + i) for i in range(3)]
    poller, buf, _ = _make_poller(rows)
    await poller.start()
    try:
        await asyncio.sleep(0.05)
    finally:
        await poller.stop()

    assert len(buf) >= 3
    latest = buf.latest_row()
    assert latest is not None
    # lineage 컬럼 strip
    assert "ingested_at" not in latest
    assert "id" not in latest
    # 도메인 키 보존
    assert latest["nox"] in {30.0, 31.0, 32.0}
    assert latest["power"] == 165.0
    assert latest["vnpr_p"] == 1.5


@pytest.mark.asyncio
async def test_tick_normalizes_measured_at_to_iso_string():
    """datetime measured_at → ISO 8601 + Z 문자열로 정규화 (RealtimeEngine kafka_ts 호환)."""
    base = datetime(2026, 5, 15, 10, 0, 1, tzinfo=timezone.utc)
    rows = [_row(1, base)]
    poller, buf, _ = _make_poller(rows)
    await poller.start()
    try:
        await asyncio.sleep(0.05)
    finally:
        await poller.stop()

    latest = buf.latest_row()
    assert latest is not None
    assert isinstance(latest["measured_at"], str)
    assert latest["measured_at"].endswith("Z")
    assert "2026-05-15T10:00:01" in latest["measured_at"]


@pytest.mark.asyncio
async def test_last_seen_advances_to_last_row_composite_cursor():
    """ASC 정렬 가정 — cursor가 마지막 row.(ingested_at, id)로 전진."""
    base = datetime(2026, 5, 15, 10, 0, 1)
    rows = [_row(i + 1, base + timedelta(seconds=i)) for i in range(3)]
    poller, _, _ = _make_poller(
        rows, initial_latest=(base - timedelta(seconds=1), 0),
    )
    await poller.start()
    try:
        await asyncio.sleep(0.05)
    finally:
        await poller.stop()

    assert poller.last_seen == (base + timedelta(seconds=2), 3)


@pytest.mark.asyncio
async def test_same_ingested_at_tie_advances_via_id():
    """동일 ingested_at + 다른 id row 묶음에서 id로 cursor 전진(M1 회귀 보호)."""
    ts = datetime(2026, 5, 15, 10, 0, 1)
    rows = [_row(i + 1, ts) for i in range(3)]  # id=1,2,3 모두 동일 ts
    poller, _, _ = _make_poller(rows, initial_latest=(ts, 0))
    await poller.start()
    try:
        await asyncio.sleep(0.05)
    finally:
        await poller.stop()

    assert poller.last_seen == (ts, 3)


@pytest.mark.asyncio
async def test_empty_fetch_does_not_advance_cursor():
    initial = (datetime(2026, 5, 15, 10, 0, 0), 0)
    poller, _, _ = _make_poller([], initial_latest=initial)
    await poller.start()
    try:
        await asyncio.sleep(0.05)
    finally:
        await poller.stop()
    assert poller.last_seen == initial


@pytest.mark.asyncio
async def test_consecutive_failures_mark_down_after_threshold():
    """5회 연속 실패 시 is_down=True + last_error 보존."""
    poller, _, _ = _make_poller(RuntimeError("db boom"))
    await poller.start()
    try:
        await asyncio.sleep(0.15)
    finally:
        await poller.stop()

    assert poller.is_down is True
    assert poller.last_error is not None
    assert "db boom" in poller.last_error


@pytest.mark.asyncio
async def test_recovery_resets_failure_state():
    """down 상태에서 다음 fetch 성공 시 자동 복구."""
    base = datetime(2026, 5, 15, 10, 0, 1)
    repo = AsyncMock()
    repo.latest_cursor.return_value = (base - timedelta(seconds=1), 0)

    call_counter = {"n": 0}
    success_row = _row(1, base)

    async def fetch_side_effect(*args, **kwargs):
        call_counter["n"] += 1
        if call_counter["n"] <= 5:
            raise RuntimeError("db boom")
        return [success_row]

    repo.fetch_since.side_effect = fetch_side_effect
    buf = SensorBuffer(maxlen=900)
    poller = SensorStreamPoller(repo, buf, poll_interval_sec=0.01)

    await poller.start()
    try:
        await asyncio.sleep(0.25)
    finally:
        await poller.stop()

    assert poller.is_down is False
    assert poller.last_error is None
    assert len(buf) >= 1


@pytest.mark.asyncio
async def test_start_with_repo_init_failure_does_not_crash():
    """latest_cursor 초기 조회 실패 시 down 상태로 시작하되 crash 없음."""
    repo = AsyncMock()
    repo.latest_cursor.side_effect = RuntimeError("init boom")
    buf = SensorBuffer(maxlen=900)
    poller = SensorStreamPoller(repo, buf, poll_interval_sec=0.01)

    await poller.start()
    try:
        await asyncio.sleep(0.02)
    finally:
        await poller.stop()

    assert poller.is_down is True
    assert poller.last_seen is None


@pytest.mark.asyncio
async def test_stop_is_idempotent():
    poller, _, _ = _make_poller([])
    await poller.start()
    await poller.stop()
    await poller.stop()  # double stop must not raise
