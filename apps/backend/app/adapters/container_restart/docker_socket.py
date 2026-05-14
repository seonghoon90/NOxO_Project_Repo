"""docker SDK 경유 컨테이너 재시작 어댑터.

`docker.from_env()`는 `DOCKER_HOST` 환경변수를 자동 honor한다.
운영 환경(compose)에서는 `DOCKER_HOST=tcp://docker-socket-proxy:2375`로
proxy 경유, 로컬 dev에서 unset이면 default unix socket 시도.
어느 쪽이든 데몬 응답이 없으면 `is_available() → False`로 폴백.

실패 케이스는 로깅 후 swallow — 백그라운드 task에서 호출되므로
예외를 raise해도 클라이언트는 이미 응답을 받은 상태.
"""

import asyncio
import logging

import docker
from docker.errors import APIError, NotFound

logger = logging.getLogger(__name__)

_RESTART_TIMEOUT_SECONDS = 10


class DockerSocketAdapter:
    def __init__(self) -> None:
        self._client = None
        self._init_error: str | None = None
        try:
            self._client = docker.from_env()
        except Exception as exc:
            self._init_error = str(exc)
            logger.warning("docker_socket_init_failed err=%s", exc)

    def is_available(self) -> bool:
        if self._client is None:
            return False
        try:
            return bool(self._client.ping())
        except Exception as exc:
            logger.warning("docker_socket_ping_failed err=%s", exc)
            return False

    async def restart(self, container_name: str) -> None:
        if self._client is None:
            logger.warning(
                "restart_skipped container=%s reason=client_unavailable",
                container_name,
            )
            return
        await asyncio.to_thread(self._restart_sync, container_name)

    def _restart_sync(self, container_name: str) -> None:
        try:
            container = self._client.containers.get(container_name)
            container.restart(timeout=_RESTART_TIMEOUT_SECONDS)
            logger.info("container_restarted name=%s", container_name)
        except NotFound:
            logger.warning("container_not_found name=%s", container_name)
        except APIError as exc:
            logger.warning("container_restart_failed name=%s err=%s", container_name, exc)
        except Exception as exc:
            # TCP DOCKER_HOST 경유 시 requests/urllib3/OSError 등이 leak될 수 있다.
            # raise 시 producer→backend 순차 재시작에서 backend 재시작이 skip되므로 swallow.
            logger.warning(
                "container_restart_unexpected_error name=%s err=%s",
                container_name, exc,
            )
