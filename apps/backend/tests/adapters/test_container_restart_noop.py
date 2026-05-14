"""NoopRestartAdapter 단위 테스트."""

import pytest

from app.adapters.container_restart.base import ContainerRestartAdapter
from app.adapters.container_restart.noop import NoopRestartAdapter


def test_noop_restart_adapter_implements_protocol():
    adapter = NoopRestartAdapter()
    assert isinstance(adapter, ContainerRestartAdapter)


def test_noop_restart_adapter_is_never_available():
    adapter = NoopRestartAdapter()
    assert adapter.is_available() is False


@pytest.mark.asyncio
async def test_noop_restart_does_nothing_silently():
    adapter = NoopRestartAdapter()
    # restart는 호출돼도 예외 없이 통과해야 함 (운영자가 잘못 호출했을 때 안전)
    await adapter.restart("any-container-name")
