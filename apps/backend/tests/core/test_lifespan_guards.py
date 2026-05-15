"""lifespan 진입부 환경변수 정합성 가드 검증.

무거운 init(ML/Kafka/CSV) 전에 미스컨피그를 즉시 fail 시키는지 확인.
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI

from app.config import Settings
from app.core.lifespan import lifespan


def _settings(**overrides) -> Settings:
    """test용 Settings — lru_cache 우회용 직접 생성."""
    base = dict(
        DATABASE_URL=None,
        KAFKA_STREAM_ENABLED=False,
        SENSOR_STREAM_POLL_ENABLED=False,
    )
    base.update(overrides)
    return Settings(**base)


@pytest.mark.asyncio
async def test_lifespan_raises_when_both_stream_modes_enabled():
    """SENSOR_STREAM_POLL_ENABLED + KAFKA_STREAM_ENABLED 동시 true → 즉시 RuntimeError."""
    bad = _settings(
        KAFKA_STREAM_ENABLED=True,
        SENSOR_STREAM_POLL_ENABLED=True,
        DATABASE_URL="postgresql://stub",
    )
    with patch("app.core.lifespan.get_settings", return_value=bad):
        with pytest.raises(RuntimeError, match="동시 활성화 불가"):
            async with lifespan(FastAPI()):
                pass


@pytest.mark.asyncio
async def test_lifespan_raises_when_poll_enabled_without_database_url():
    """SENSOR_STREAM_POLL_ENABLED=true인데 DATABASE_URL 없으면 즉시 RuntimeError."""
    bad = _settings(SENSOR_STREAM_POLL_ENABLED=True, DATABASE_URL=None)
    with patch("app.core.lifespan.get_settings", return_value=bad):
        with pytest.raises(RuntimeError, match="DATABASE_URL 설정 필수"):
            async with lifespan(FastAPI()):
                pass
