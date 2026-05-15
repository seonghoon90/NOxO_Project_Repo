"""SensorStreamRepository — sensor_data_stream 폴링 경로 검증."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.repositories.sensor_stream_repo import SensorStreamRepository


@pytest.fixture
def mock_session_factory():
    """sensor_repo 테스트와 동일 패턴 — 동기 sessionmaker mock."""
    session = MagicMock()
    factory = MagicMock()
    factory.return_value.__enter__ = MagicMock(return_value=session)
    factory.return_value.__exit__ = MagicMock(return_value=None)
    return factory, session


def _set_rows(session, rows):
    session.execute.return_value.mappings.return_value.all.return_value = rows


def _set_first(session, row):
    session.execute.return_value.mappings.return_value.first.return_value = row


def _stream_row(
    row_id: int,
    ingested_at: datetime,
    measured_at: datetime,
    nox_ppm: float = 30.0,
    o2_pct: float | None = 10.0,
) -> dict:
    """DB 컬럼명으로 row 모킹 — repo가 도메인 키로 변환해 반환한다."""
    return {
        "id": row_id,
        "measured_at": measured_at,
        "ingested_at": ingested_at,
        "syngas_flow": 100.0,
        "igv_opening": 80.0,
        "n2_offset": 5.0,
        "n2_valve_1": 42.0,
        "syngas_srv": 60.0,
        "syngas_gcv_1": 55.0,
        "syngas_gcv_1a": 54.0,
        "syngas_gcv_2": 53.0,
        "ibh_valve": 30.0,
        "n2_flow": 25.0,
        "nox_ppm": nox_ppm,
        "exhaust_temp": 580.0,
        "power_mw": 165.0,
        "npr_primary": 1.5,
        "o2_pct": o2_pct,
    }


@pytest.mark.asyncio
async def test_fetch_since_translates_db_columns_to_domain_keys(mock_session_factory):
    """DB nox_ppm/power_mw/npr_primary → 도메인 nox/power/vnpr_p.
    tags.py::ALL_TAGS_TO_DOMAIN과 키 정합 — RealtimeEngine forecaster 호환."""
    factory, session = mock_session_factory
    base = datetime(2026, 5, 15, 10, 0, 0)
    rows = [_stream_row(1, base, base, nox_ppm=33.0)]
    _set_rows(session, rows)

    repo = SensorStreamRepository(factory)
    result = await repo.fetch_since((base - timedelta(seconds=1), 0), limit=10)

    assert len(result) == 1
    row = result[0]
    # 도메인 키로 변환됨
    assert row["nox"] == 33.0
    assert row["power"] == 165.0
    assert row["vnpr_p"] == 1.5
    assert row["o2_pct"] == 10.0
    # DB 컬럼명은 더 이상 노출되지 않음
    assert "nox_ppm" not in row
    assert "power_mw" not in row
    assert "npr_primary" not in row
    # 11개 동일명은 그대로
    assert row["syngas_flow"] == 100.0
    assert row["exhaust_temp"] == 580.0


@pytest.mark.asyncio
async def test_fetch_since_empty_when_no_new_rows(mock_session_factory):
    factory, session = mock_session_factory
    _set_rows(session, [])
    repo = SensorStreamRepository(factory)
    result = await repo.fetch_since((datetime(2026, 5, 15, 10, 0, 0), 0), limit=10)
    assert result == []


@pytest.mark.asyncio
async def test_fetch_since_rejects_none_cursor(mock_session_factory):
    """None cursor는 explicit error — 호출자가 latest_cursor로 초기화 필요."""
    factory, _ = mock_session_factory
    repo = SensorStreamRepository(factory)
    with pytest.raises(ValueError, match="cursor required"):
        await repo.fetch_since(None)


@pytest.mark.asyncio
async def test_fetch_since_passes_composite_cursor_to_query(mock_session_factory):
    """SQL 바인드 파라미터로 (cursor_ts, cursor_id, limit)이 정확히 전달."""
    factory, session = mock_session_factory
    _set_rows(session, [])
    repo = SensorStreamRepository(factory)
    cursor_ts = datetime(2026, 5, 15, 10, 0, 0)
    await repo.fetch_since((cursor_ts, 42), limit=50)
    params = session.execute.call_args[0][1]
    assert params == {"cursor_ts": cursor_ts, "cursor_id": 42, "limit": 50}


@pytest.mark.asyncio
async def test_fetch_since_does_not_filter_out_bootstrap_rows(mock_session_factory):
    """producer loop reset 시 bootstrap upsert도 SensorBuffer로 전달되어야 한다."""
    factory, session = mock_session_factory
    _set_rows(session, [])
    repo = SensorStreamRepository(factory)
    await repo.fetch_since((datetime(2026, 5, 15, 10, 0, 0), 0), limit=10)

    sql = str(session.execute.call_args[0][0])
    assert "ingest_mode = 'stream'" not in sql


@pytest.mark.asyncio
async def test_latest_cursor_returns_tuple(mock_session_factory):
    factory, session = mock_session_factory
    latest_ts = datetime(2026, 5, 15, 10, 5, 0)
    _set_first(session, {"ingested_at": latest_ts, "id": 100})
    repo = SensorStreamRepository(factory)
    assert await repo.latest_cursor() == (latest_ts, 100)


@pytest.mark.asyncio
async def test_latest_cursor_returns_none_for_empty_table(mock_session_factory):
    factory, session = mock_session_factory
    _set_first(session, None)
    repo = SensorStreamRepository(factory)
    assert await repo.latest_cursor() is None
