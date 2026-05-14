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
        # 진행 중 task 가시화 — 실패/취소로 끝난 이전 task의 예외를 silently 묻지
        # 않도록 done 상태에서 결과를 1회 로깅 후 새 reset을 허용한다.
        # 체크와 set 사이에 await를 넣지 말 것 — race 발생 시 split-brain 재시작.
        if self._pending_task is not None:
            if not self._pending_task.done():
                raise ResetAlreadyInProgressError()
            # cancel된 task의 .exception() 호출은 CancelledError를 raise하므로 분리 처리.
            if self._pending_task.cancelled():
                logger.warning(
                    "previous_reset_task_cancelled — 새 reset 허용",
                )
            else:
                prior_exc = self._pending_task.exception()
                if prior_exc is not None:
                    logger.warning(
                        "previous_reset_task_ended_with_error err=%r — 새 reset 허용",
                        prior_exc,
                    )
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
        # CancelledError 정책: producer가 cancel되어도 backend 재시작 시도를
        # 보장한다(spec §7 invariant 우선). 이후 try/finally의 finally에서 cancel을
        # 재전파해 호출자(lifespan shutdown)의 cancel 의도를 보존한다.
        producer_cancelled = False
        backend_cancelled = False
        try:
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
                backend_cancelled = True
            except Exception as exc:
                logger.warning("delayed_restart_backend_failed err=%s", exc)
        finally:
            # 어느 쪽이든 cancel을 받았다면 호출자에게 명시적으로 전파한다.
            # finally 블록에 두어 backend try가 raise하지 않더라도 동일 정책 적용.
            if producer_cancelled or backend_cancelled:
                raise asyncio.CancelledError()
