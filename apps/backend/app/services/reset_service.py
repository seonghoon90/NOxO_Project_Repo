"""리셋 비밀번호 검증 + 백그라운드 컨테이너 재시작 서비스.

검증 순서: 비밀번호 미설정 → docker 미가용 → 비밀번호 불일치.
재시작 순서: producer 먼저, backend 나중 (backend가 죽으면 후속 호출 불가).
"""

import asyncio
import hmac
import logging

from app.adapters.container_restart import ContainerRestartAdapter
from app.exceptions import InvalidResetPasswordError, ResetUnavailableError
from app.schemas.reset import ResetResponse

logger = logging.getLogger(__name__)

_DEFAULT_DELAY_SECONDS = 2.0


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
        # (Python 공식 권고). 동시 다중 리셋은 dedupe하지 않으므로
        # 두 번째 리셋이 첫 task 참조를 덮어쓸 수 있지만, 두 task 모두
        # 동일한 producer/backend 재시작을 수행하므로 의도된 결과는 보존된다.
        self._pending_task: asyncio.Task | None = None

    async def schedule_reset(self, password: str) -> ResetResponse:
        if not self._reset_password:
            raise ResetUnavailableError("reset password not configured")
        if not self._restart_adapter.is_available():
            raise ResetUnavailableError(
                "docker socket not mounted or docker daemon unreachable"
            )
        if not hmac.compare_digest(password, self._reset_password):
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
        # 어댑터(`_restart_sync`)가 모든 예외를 swallow하므로 사실상 raise는 일어나지
        # 않지만, defense-in-depth로 두 호출을 별도 try 블록으로 격리한다.
        # CancelledError는 lifespan shutdown 또는 backend 자기 자신이 docker에
        # 의해 강제 종료되는 정상 경로이므로 INFO로 분리 — WARNING 잡음 회피.
        try:
            await self._restart_adapter.restart(self._producer_container)
        except asyncio.CancelledError:
            logger.info("delayed_restart_producer_cancelled (expected on shutdown)")
            raise
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
