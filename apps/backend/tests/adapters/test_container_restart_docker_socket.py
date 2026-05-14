"""DockerSocketAdapter 단위 테스트 (docker SDK Mock)."""

from unittest.mock import MagicMock, patch

import pytest

from app.adapters.container_restart.docker_socket import DockerSocketAdapter


def _patch_from_env(client_mock: MagicMock):
    return patch(
        "app.adapters.container_restart.docker_socket.docker.from_env",
        return_value=client_mock,
    )


def test_is_available_true_when_ping_succeeds():
    client = MagicMock()
    client.ping.return_value = True
    with _patch_from_env(client):
        adapter = DockerSocketAdapter()
        assert adapter.is_available() is True


def test_is_available_false_when_ping_raises():
    client = MagicMock()
    client.ping.side_effect = OSError("docker socket missing")
    with _patch_from_env(client):
        adapter = DockerSocketAdapter()
        assert adapter.is_available() is False


def test_is_available_false_when_from_env_raises():
    with patch(
        "app.adapters.container_restart.docker_socket.docker.from_env",
        side_effect=OSError("no docker"),
    ):
        adapter = DockerSocketAdapter()
        assert adapter.is_available() is False


@pytest.mark.asyncio
async def test_restart_invokes_docker_containers_restart():
    container = MagicMock()
    client = MagicMock()
    client.ping.return_value = True
    client.containers.get.return_value = container
    with _patch_from_env(client):
        adapter = DockerSocketAdapter()
        await adapter.restart("kafka-producer")
    client.containers.get.assert_called_once_with("kafka-producer")
    container.restart.assert_called_once_with(timeout=10)


@pytest.mark.asyncio
async def test_restart_swallows_not_found_with_log(caplog):
    from docker.errors import NotFound

    client = MagicMock()
    client.ping.return_value = True
    client.containers.get.side_effect = NotFound("container missing")
    with _patch_from_env(client):
        adapter = DockerSocketAdapter()
        with caplog.at_level("WARNING"):
            await adapter.restart("ghost-container")
    assert any("ghost-container" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_restart_swallows_unexpected_exception_with_log(caplog):
    """proxy TCP 끊김 등으로 발생할 수 있는 임의 예외도 swallow + log."""

    client = MagicMock()
    client.ping.return_value = True
    client.containers.get.side_effect = OSError("connection refused")
    with _patch_from_env(client):
        adapter = DockerSocketAdapter()
        with caplog.at_level("WARNING"):
            # raise되지 않아야 한다 — producer 재시작 실패가 backend 재시작을
            # 막지 않도록 보장하는 핵심 invariant.
            await adapter.restart("kafka-producer")
    assert any("kafka-producer" in rec.message for rec in caplog.records)
