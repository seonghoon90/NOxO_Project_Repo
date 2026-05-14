"""ResetService 단위 테스트."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from app.exceptions import InvalidResetPasswordError, ResetUnavailableError
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
