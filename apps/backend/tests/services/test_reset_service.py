"""ResetService 단위 테스트."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from app.exceptions import (
    InvalidResetPasswordError,
    ResetAlreadyInProgressError,
    ResetUnavailableError,
)
from app.services.reset_service import ResetService


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
    """회귀: _pending_task가 살아있을 때 두 번째 호출은 409로 거부된다."""
    service, adapter = _make_service(reset_password="secret", delay_seconds=0.0)

    # 첫 호출이 await중이도록 restart를 영구 대기시킴
    pending_event = asyncio.Event()

    async def block_forever(_name: str) -> None:
        await pending_event.wait()

    adapter.restart = AsyncMock(side_effect=block_forever)

    response1 = await service.schedule_reset(password="secret")
    assert response1.status == "restarting"
    # 첫 task가 _delayed_restart 안에서 producer restart를 await하도록 한 tick 양보
    await asyncio.sleep(0)

    # 두 번째 호출은 진행 중 task를 감지해 409 raise
    with pytest.raises(ResetAlreadyInProgressError):
        await service.schedule_reset(password="secret")

    # 첫 task만 살아있어야 한다 (두 번째 호출이 _pending_task를 덮어쓰지 않음)
    pending_event.set()
    service._pending_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await service._pending_task


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
async def test_default_delay_is_5_seconds():
    """회귀: nginx buffering 환경 안전을 위해 default delay 5초."""
    service, _ = _make_service(reset_password="secret")
    # delay_seconds 인자 없이 default 사용
    service_default = ResetService(
        restart_adapter=service._restart_adapter,
        backend_container="noxo-backend",
        producer_container="kafka-producer",
        reset_password="secret",
    )
    assert service_default._delay_seconds == 5.0
