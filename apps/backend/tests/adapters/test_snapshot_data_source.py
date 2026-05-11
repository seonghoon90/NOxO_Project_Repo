from unittest.mock import AsyncMock
import pandas as pd
import pytest

from app.adapters.data_source.snapshot import SnapshotDataSource
from app.exceptions import DataNotEnoughError
from digital_twin.preprocess import RAW_FEATURES, TARGETS


def _fake_snapshot_df(rows: int = 900) -> pd.DataFrame:
    cols = ["measured_at"] + list(RAW_FEATURES) + list(TARGETS)
    data = {c: [0.0] * rows if c != "measured_at"
            else pd.date_range("2026-05-11", periods=rows, freq="1s")
            for c in cols}
    return pd.DataFrame(data)


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.fetch_recent_window.return_value = _fake_snapshot_df(900)
    return repo


async def test_get_initial_snapshot_calls_repo_with_correct_seconds(mock_repo):
    """window_minutes=15 → seconds=900으로 repo 호출."""
    src = SnapshotDataSource(mock_repo)
    await src.get_initial_snapshot(window_minutes=15)
    mock_repo.fetch_recent_window.assert_called_once_with(seconds=900)


async def test_validate_raises_when_rows_insufficient(mock_repo):
    """행 수 < required면 DataNotEnoughError."""
    mock_repo.fetch_recent_window.return_value = _fake_snapshot_df(500)
    src = SnapshotDataSource(mock_repo)
    with pytest.raises(DataNotEnoughError):
        await src.get_initial_snapshot(window_minutes=15)


async def test_validate_raises_when_time_gap_detected(mock_repo):
    """인접 행 간 > 2초 gap → DataNotEnoughError."""
    df = _fake_snapshot_df(900)
    # 5번째 행에 5초 gap 삽입
    df.loc[5, "measured_at"] = df.loc[5, "measured_at"] + pd.Timedelta(seconds=5)
    mock_repo.fetch_recent_window.return_value = df
    src = SnapshotDataSource(mock_repo)
    with pytest.raises(DataNotEnoughError, match="time gap"):
        await src.get_initial_snapshot(window_minutes=15)


async def test_poll_latest_returns_none(mock_repo):
    """B안 고정 모드는 None 반환."""
    src = SnapshotDataSource(mock_repo)
    assert src.poll_latest() is None


async def test_get_at_timestamp_raises_not_implemented(mock_repo):
    """리플레이 모드는 미구현."""
    src = SnapshotDataSource(mock_repo)
    with pytest.raises(NotImplementedError):
        src.get_at_timestamp(pd.Timestamp("2026-05-11"), window_minutes=15)
