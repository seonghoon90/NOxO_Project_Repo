from unittest.mock import MagicMock
import pandas as pd
import pytest

from app.repositories.sensor_repo import SensorRepository, TAG_TO_DB_COLUMN
from digital_twin.preprocess import RAW_FEATURES, TARGETS


@pytest.fixture
def mock_session_factory():
    """동기 SQLAlchemy session mock (R5 / R-A6 — 4차 보강).

    SensorRepository._fetch_sync는 sessionmaker[Session] 동기 컨텍스트 매니저 사용 →
    MagicMock + __enter__/__exit__로 모킹. 외부 fetch_recent_window는 asyncio.to_thread로
    sync 호출을 await 가능하게 감싸므로 테스트 본문은 여전히 `await` 사용.
    """
    session = MagicMock()
    factory = MagicMock()
    factory.return_value.__enter__ = MagicMock(return_value=session)
    factory.return_value.__exit__ = MagicMock(return_value=None)
    return factory, session


# B6 (5차 보강) — module-level helper.
def _set_rows(session, rows):
    """`session.execute(sql, params).mappings().all()` 경로를 모킹."""
    session.execute.return_value.mappings.return_value.all.return_value = rows


async def test_fetch_recent_window_returns_correct_columns(mock_session_factory):
    """총 43컬럼(measured_at + RAW 39 + TARGETS 3)이 모두 포함된다."""
    factory, session = mock_session_factory
    cols = ["measured_at"] + list(RAW_FEATURES) + list(TARGETS)
    fake_rows = [
        {c: 0.0 if c != "measured_at" else pd.Timestamp("2026-05-11 00:00:00") for c in cols}
        for _ in range(900)
    ]
    _set_rows(session, fake_rows)
    repo = SensorRepository(factory)
    df = await repo.fetch_recent_window(seconds=900)
    assert len(df.columns) == 43
    assert "measured_at" in df.columns
    for tag in RAW_FEATURES:
        assert tag in df.columns


async def test_fetch_recent_window_renames_db_columns_to_tags(mock_session_factory):
    """TAG_TO_DB_COLUMN 매핑에 따라 DB 컬럼명을 태그명으로 복원한다."""
    factory, session = mock_session_factory
    _set_rows(session, [
        {"measured_at": pd.Timestamp("2026-05-11"), **{TAG_TO_DB_COLUMN[t]: 1.0 for t in list(RAW_FEATURES) + list(TARGETS)}}
    ])
    repo = SensorRepository(factory)
    df = await repo.fetch_recent_window(seconds=900)
    for tag in RAW_FEATURES:
        assert tag in df.columns


async def test_fetch_recent_window_respects_seconds_param(mock_session_factory):
    """seconds=900 → SQL params dict의 `n` 키로 전달 (R-A2 — 4차 보강)."""
    factory, session = mock_session_factory
    _set_rows(session, [])
    repo = SensorRepository(factory)
    await repo.fetch_recent_window(seconds=900)
    args, kwargs = session.execute.call_args
    assert len(args) >= 2, "session.execute는 (sql, params) 두 인자로 호출되어야 함"
    sql_arg, params = args[0], args[1]
    assert ":n" in str(sql_arg), "SQL에 :n placeholder가 존재해야 함"
    assert params == {"n": 900}


async def test_fetch_recent_window_measured_at_is_datetime(mock_session_factory):
    """R-A3 — 4차 보강: DB driver가 string 반환해도 measured_at은 datetime dtype 보장."""
    factory, session = mock_session_factory
    cols = ["measured_at"] + list(RAW_FEATURES) + list(TARGETS)
    fake_rows = [
        {c: "2026-05-11 00:00:00" if c == "measured_at" else 0.0 for c in cols}
        for _ in range(3)
    ]
    _set_rows(session, fake_rows)
    repo = SensorRepository(factory)
    df = await repo.fetch_recent_window(seconds=3)
    assert pd.api.types.is_datetime64_any_dtype(df["measured_at"])


async def test_fetch_recent_window_invalid_timestamp_raises(mock_session_factory):
    """A3 — 5차 보강: 잘못된 timestamp는 NaT silent 폴백이 아닌 ValueError로 raise."""
    factory, session = mock_session_factory
    cols = ["measured_at"] + list(RAW_FEATURES) + list(TARGETS)
    fake_rows = [
        {c: "not-a-timestamp" if c == "measured_at" else 0.0 for c in cols}
    ]
    _set_rows(session, fake_rows)
    repo = SensorRepository(factory)
    with pytest.raises((ValueError, Exception)):
        await repo.fetch_recent_window(seconds=1)


async def test_fetch_recent_window_db_failure_raises(mock_session_factory):
    """DB 연결 실패 시 예외 전파."""
    factory, session = mock_session_factory
    session.execute.side_effect = ConnectionError("db down")
    repo = SensorRepository(factory)
    with pytest.raises(ConnectionError):
        await repo.fetch_recent_window(seconds=900)
