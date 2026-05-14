"""리셋 비밀번호 검증 + 백그라운드 컨테이너 재시작 서비스.

검증 순서: 비밀번호 미설정 → docker 미가용 → 진행 중 task 존재 → 비밀번호 불일치.
재시작 순서: producer 먼저, backend 나중 (backend가 죽으면 후속 호출 불가).
"""

import asyncio
import hmac
import logging

from app.adapters.container_restart import ContainerRestartAdapter
from app.exceptions import (
    InvalidResetPasswordError,
    ResetAlreadyInProgressError,
    ResetUnavailableError,
)
from app.schemas.reset import ResetResponse

logger = logging.getLogger(__name__)

# nginx buffering + producer restart timeout(10s) 환경에서도 응답이 client에
# flush될 시간을 확보하려면 self-restart 전 5초가 안전 마진. 2초는 reverse-proxy
# 환경에서 응답 도달 전 backend가 죽을 위험이 있다.
_DEFAULT_DELAY_SECONDS = 5.0


class ResetService:
    def __init__(
        self,
        *,
        restart_adapter: ContainerRestartAdapter,
        backend_container: str,
        producer_container: str,
        reset_password: str | None,
        delay_seconds: float = _DEFAULT_DELAY_SECONDS,
    ) -> None:
        self._restart_adapter = restart_adapter
        self._backend_container = backend_container
        self._producer_container = producer_container
        self._reset_password = reset_password
        self._delay_seconds = delay_seconds
        # asyncio.create_task 결과는 강참조로 보관해야 GC로 사라지지 않는다
        # (Python 공식 권고). 동시 호출은 ResetAlreadyInProgressError로 거부해
        # 동일 컨테이너에 대한 split-brain restart를 방지한다.
        self._pending_task: asyncio.Task | None = None

    async def schedule_reset(self, password: str) -> ResetResponse:
        if not self._reset_password:
            raise ResetUnavailableError("reset password not configured")
        if not self._restart_adapter.is_available():
            raise ResetUnavailableError(
                "docker socket not mounted or docker daemon unreachable"
            )
        if self._pending_task is not None and not self._pending_task.done():
            raise ResetAlreadyInProgressError()
        # hmac.compare_digest는 양쪽이 모두 str(ASCII)이거나 모두 bytes여야 한다.
        # 비-ASCII 입력 시 TypeError → 500 응답에 traceback이 노출돼
        # 비밀번호 측면 채널이 될 수 있어 bytes(utf-8)로 정규화한다.
        password_bytes = password.encode("utf-8")
        expected_bytes = self._reset_password.encode("utf-8")
        if not hmac.compare_digest(password_bytes, expected_bytes):
            raise InvalidResetPasswordError()

        self._pending_task = asyncio.create_task(self._delayed_restart())
        return ResetResponse(
            status="restarting",
            message="Backend and producer will restart shortly",
            restart_in_seconds=self._delay_seconds,
        )

    async def _delayed_restart(self) -> None:
        await asyncio.sleep(self._delay_seconds)
        # spec §7 invariant — producer 재시작 실패는 backend 재시작을 막지 않는다.
        # 어댑터(`_restart_sync`)가 모든 예외를 swallow하지만 defense-in-depth로
        # 두 호출을 별도 try 블록으로 격리한다.
        #
        # CancelledError 처리: producer try에서 CancelledError를 raise하면 backend
        # try가 실행되지 않아 spec §7 위반이 된다. 따라서 producer cancel을 만나도
        # backend 재시작은 시도한 뒤 backend try에서 다시 raise한다 (shutdown
        # 경로면 backend도 곧 cancel되므로 무해, 일반 cancel이면 backend 재시작
        # 보장이 우선).
        producer_cancelled = False
        try:
            await self._restart_adapter.restart(self._producer_container)
        except asyncio.CancelledError:
            logger.info("delayed_restart_producer_cancelled (expected on shutdown)")
            producer_cancelled = True
        except Exception as exc:
            logger.warning(
                "delayed_restart_producer_failed err=%s — backend restart 시도 계속",
                exc,
            )
        try:
            await self._restart_adapter.restart(self._backend_container)
        except asyncio.CancelledError:
            logger.info("delayed_restart_backend_cancelled (expected on shutdown)")
            raise
        except Exception as exc:
            logger.warning("delayed_restart_backend_failed err=%s", exc)
        if producer_cancelled:
            raise asyncio.CancelledError()
