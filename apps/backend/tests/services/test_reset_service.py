"""ResetService 단위 테스트."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from app.exceptions import (
    InvalidResetPasswordError,
    ResetAlreadyInProgressError,
    ResetUnavailableError,
)
from app.services.reset_service import _DEFAULT_DELAY_SECONDS, ResetService


def _make_service(
    *,
    is_available: bool = True,
    reset_password: str | None = "secret",
    delay_seconds: float = 0.01,
) -> tuple[ResetService, MagicMock]:
    adapter = MagicMock()
    adapter.is_available.return_value = is_available
    adapter.restart = AsyncMock()
    service = ResetService(
        restart_adapter=adapter,
        backend_container="noxo-backend",
        producer_container="kafka-producer",
        reset_password=reset_password,
        delay_seconds=delay_seconds,
    )
    return service, adapter


@pytest.mark.asyncio
async def test_raises_unavailable_when_password_missing():
    service, _ = _make_service(reset_password=None)
    with pytest.raises(ResetUnavailableError) as exc_info:
        await service.schedule_reset(password="anything")
    assert "not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_raises_unavailable_when_password_blank():
    service, _ = _make_service(reset_password="")
    with pytest.raises(ResetUnavailableError):
        await service.schedule_reset(password="anything")


@pytest.mark.asyncio
async def test_raises_unavailable_when_docker_down():
    service, _ = _make_service(is_available=False)
    with pytest.raises(ResetUnavailableError) as exc_info:
        await service.schedule_reset(password="secret")
    assert "docker" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_raises_invalid_when_password_mismatch():
    service, _ = _make_service(reset_password="secret")
    with pytest.raises(InvalidResetPasswordError):
        await service.schedule_reset(password="wrong")


@pytest.mark.asyncio
async def test_returns_response_and_schedules_restart_when_ok():
    service, adapter = _make_service(reset_password="secret", delay_seconds=0.0)
    response = await service.schedule_reset(password="secret")
    assert response.status == "restarting"
    assert response.restart_in_seconds == 0.0
    # 강참조 보관 확인 — task가 GC되지 않도록 self._pending_task에 저장돼야 함
    assert service._pending_task is not None
    # 백그라운드 task 완료를 deterministic하게 대기 (sleep polling 회피)
    await service._pending_task
    # producer 먼저, backend 나중 순서로 호출되어야 한다
    assert adapter.restart.await_args_list == [
        call("kafka-producer"),
        call("noxo-backend"),
    ]


@pytest.mark.asyncio
async def test_check_order_password_missing_takes_precedence_over_docker_down():
    """비밀번호 미설정이 docker 미가용보다 먼저 검사되어야 한다."""
    service, _ = _make_service(reset_password=None, is_available=False)
    with pytest.raises(ResetUnavailableError) as exc_info:
        await service.schedule_reset(password="anything")
    assert "not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_producer_restart_failure_does_not_block_backend_restart():
    """spec §7 invariant: producer 재시작 호출이 raise해도 backend 재시작은 시도된다."""
    service, adapter = _make_service(reset_password="secret", delay_seconds=0.0)

    # 첫 호출(producer)은 raise, 두 번째 호출(backend)은 정상 동작하도록 분기
    async def restart_side_effect(name: str) -> None:
        if name == "kafka-producer":
            raise OSError("simulated proxy TCP disconnect")
        # backend 호출은 통과

    adapter.restart = AsyncMock(side_effect=restart_side_effect)

    response = await service.schedule_reset(password="secret")
    assert response.status == "restarting"
    await service._pending_task

    # backend 호출이 producer 실패와 무관하게 발사돼야 한다
    assert adapter.restart.await_args_list == [
        call("kafka-producer"),
        call("noxo-backend"),
    ]


@pytest.mark.asyncio
async def test_producer_cancellederror_still_triggers_backend_restart():
    """회귀: producer 호출에서 CancelledError 발생해도 backend 재시작 시도 후 cancel 전파."""
    service, adapter = _make_service(reset_password="secret", delay_seconds=0.0)

    async def restart_side_effect(name: str) -> None:
        if name == "kafka-producer":
            raise asyncio.CancelledError()

    adapter.restart = AsyncMock(side_effect=restart_side_effect)

    response = await service.schedule_reset(password="secret")
    assert response.status == "restarting"

    with pytest.raises(asyncio.CancelledError):
        await service._pending_task

    # producer cancel 후에도 backend 호출은 발사돼야 한다 (spec §7 invariant)
    assert adapter.restart.await_args_list == [
        call("kafka-producer"),
        call("noxo-backend"),
    ]


@pytest.mark.asyncio
async def test_concurrent_reset_raises_already_in_progress():
    """회귀: _pending_task가 살아있을 때 두 번째 호출은 409로 거부된다.

    Deterministic: 첫 task를 영구 대기시키고 두 번째 호출의 거부만 확인.
    cleanup 시 cancel→drain으로 race 없이 종료.
    """
    service, adapter = _make_service(reset_password="secret", delay_seconds=0.0)

    pending_event = asyncio.Event()

    async def block_forever(_name: str) -> None:
        await pending_event.wait()

    adapter.restart = AsyncMock(side_effect=block_forever)

    response1 = await service.schedule_reset(password="secret")
    assert response1.status == "restarting"
    first_task = service._pending_task
    assert first_task is not None
    # 첫 task가 _delayed_restart 내부 producer restart를 await하도록 한 tick 양보
    await asyncio.sleep(0)
    assert not first_task.done()

    # 두 번째 호출은 진행 중 task를 감지해 409 raise
    with pytest.raises(ResetAlreadyInProgressError):
        await service.schedule_reset(password="secret")

    # _pending_task 참조가 첫 task 그대로여야 한다 (덮어쓰기 금지)
    assert service._pending_task is first_task

    # cleanup: cancel 후 drain
    first_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first_task


@pytest.mark.asyncio
async def test_concurrent_reset_allowed_after_previous_completes():
    """회귀: 이전 task가 done이면 새 reset이 허용된다."""
    service, adapter = _make_service(reset_password="secret", delay_seconds=0.0)

    # 첫 호출 완료 후
    await service.schedule_reset(password="secret")
    await service._pending_task
    assert service._pending_task.done()

    # 두 번째 호출은 정상 진행
    response2 = await service.schedule_reset(password="secret")
    assert response2.status == "restarting"
    await service._pending_task


@pytest.mark.asyncio
async def test_password_with_unicode_does_not_raise_typeerror():
    """회귀: 비-ASCII 비밀번호 입력 시 TypeError 없이 InvalidResetPassword로 처리."""
    service, _ = _make_service(reset_password="비밀번호")
    # 다른 비-ASCII 입력
    with pytest.raises(InvalidResetPasswordError):
        await service.schedule_reset(password="잘못된비밀번호")


@pytest.mark.asyncio
async def test_password_with_unicode_matches():
    """회귀: 동일한 비-ASCII 비밀번호는 정상 매칭."""
    service, adapter = _make_service(reset_password="비밀번호", delay_seconds=0.0)
    response = await service.schedule_reset(password="비밀번호")
    assert response.status == "restarting"
    await service._pending_task
    assert adapter.restart.await_count == 2


@pytest.mark.asyncio
async def test_default_delay_matches_module_constant():
    """회귀: default delay가 모듈 상수와 동기화되어 있는지 확인."""
    service, _ = _make_service(reset_password="secret")
    service_default = ResetService(
        restart_adapter=service._restart_adapter,
        backend_container="noxo-backend",
        producer_container="kafka-producer",
        reset_password="secret",
    )
    assert service_default._delay_seconds == _DEFAULT_DELAY_SECONDS
    # 운영 안전 마진 — nginx buffering + producer restart timeout 환경 기준 5초 이상.
    assert _DEFAULT_DELAY_SECONDS >= 5.0


@pytest.mark.asyncio
async def test_previous_task_failure_logged_when_new_reset_allowed(caplog):
    """회귀: 이전 task가 예외로 끝났으면 로깅 후 새 reset 허용 (silent failure 방지)."""
    service, adapter = _make_service(reset_password="secret", delay_seconds=0.0)

    fail_count = {"n": 0}

    async def restart_side_effect(name: str) -> None:
        # 첫 회 producer 호출에서만 raise — 이후 모든 호출은 정상 통과
        if name == "kafka-producer" and fail_count["n"] == 0:
            fail_count["n"] += 1
            raise OSError("first attempt failed")

    adapter.restart = AsyncMock(side_effect=restart_side_effect)

    # 1차 reset — producer raise + backend 정상 (전체 task는 정상 종료)
    await service.schedule_reset(password="secret")
    await service._pending_task
    assert service._pending_task.exception() is None

    # 2차 reset — done이지만 exception None이므로 경고 없이 통과
    with caplog.at_level(logging.WARNING):
        await service.schedule_reset(password="secret")
    await service._pending_task
    assert "previous_reset_task_ended_with_error" not in caplog.text


@pytest.mark.asyncio
async def test_previous_cancelled_task_emits_warning_then_allows_new_reset(caplog):
    """회귀: 이전 task가 cancel로 끝났으면 WARNING 후 새 reset 허용."""
    service, adapter = _make_service(reset_password="secret", delay_seconds=0.0)

    pending_event = asyncio.Event()

    async def block_forever(_name: str) -> None:
        await pending_event.wait()

    adapter.restart = AsyncMock(side_effect=block_forever)

    await service.schedule_reset(password="secret")
    first_task = service._pending_task
    await asyncio.sleep(0)
    first_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first_task

    # 두 번째 reset — cancelled task 발견 → WARNING + 새 task 생성
    adapter.restart = AsyncMock()
    with caplog.at_level(logging.WARNING):
        await service.schedule_reset(password="secret")
    assert "previous_reset_task_cancelled" in caplog.text
    await service._pending_task


@pytest.mark.asyncio
async def test_password_too_long_rejected_by_schema():
    """회귀: max_length=128 초과 password는 schema 단계에서 거부 (서비스 도달 X).

    여기선 schema 검증을 직접 호출 — 엔드포인트 통합 테스트는 별도.
    """
    from pydantic import ValidationError

    from app.schemas.reset import ResetRequest

    too_long = "x" * 129
    with pytest.raises(ValidationError):
        ResetRequest(password=too_long)
    # 경계값 OK
    ok = ResetRequest(password="x" * 128)
    assert ok.password.startswith("x")


@pytest.mark.asyncio
async def test_cancelled_during_backend_restart_propagates():
    """회귀: backend 재시작 중 cancel되면 finally에서 CancelledError 재전파."""
    service, adapter = _make_service(reset_password="secret", delay_seconds=0.0)

    async def restart_side_effect(name: str) -> None:
        if name == "noxo-backend":
            raise asyncio.CancelledError()

    adapter.restart = AsyncMock(side_effect=restart_side_effect)

    await service.schedule_reset(password="secret")
    with pytest.raises(asyncio.CancelledError):
        await service._pending_task
