"""POST /api/reset 엔드포인트 통합 테스트 (ResetService dependency_override)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_reset_service
from app.exceptions import InvalidResetPasswordError, ResetUnavailableError
from app.main import app
from app.schemas.reset import ResetResponse


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _override_with(service):
    app.dependency_overrides[get_reset_service] = lambda: service


def test_returns_200_with_reset_response_on_success():
    service = MagicMock()
    service.schedule_reset = AsyncMock(
        return_value=ResetResponse(
            status="restarting",
            message="Backend and producer will restart shortly",
            restart_in_seconds=5.0,
        )
    )
    _override_with(service)

    with TestClient(app) as client:
        res = client.post("/api/reset", json={"password": "secret"})

    assert res.status_code == 200
    assert res.json() == {
        "status": "restarting",
        "message": "Backend and producer will restart shortly",
        "restart_in_seconds": 5.0,
    }
    service.schedule_reset.assert_awaited_once_with(password="secret")


def test_returns_401_on_invalid_password():
    service = MagicMock()
    service.schedule_reset = AsyncMock(side_effect=InvalidResetPasswordError())
    _override_with(service)

    with TestClient(app) as client:
        res = client.post("/api/reset", json={"password": "wrong"})

    assert res.status_code == 401
    body = res.json()
    assert body["error_code"] == "INVALID_RESET_PASSWORD"
    assert body["detail"] == "Reset password does not match"


def test_returns_503_when_password_not_configured():
    service = MagicMock()
    service.schedule_reset = AsyncMock(
        side_effect=ResetUnavailableError("reset password not configured")
    )
    _override_with(service)

    with TestClient(app) as client:
        res = client.post("/api/reset", json={"password": "x"})

    assert res.status_code == 503
    body = res.json()
    assert body["error_code"] == "RESET_UNAVAILABLE"
    assert "not configured" in body["detail"]


def test_returns_503_when_docker_unavailable():
    service = MagicMock()
    service.schedule_reset = AsyncMock(
        side_effect=ResetUnavailableError("docker socket not mounted or docker daemon unreachable")
    )
    _override_with(service)

    with TestClient(app) as client:
        res = client.post("/api/reset", json={"password": "x"})

    assert res.status_code == 503
    assert "docker" in res.json()["detail"].lower()


def test_returns_422_when_password_missing():
    service = MagicMock()
    service.schedule_reset = AsyncMock()
    _override_with(service)

    with TestClient(app) as client:
        res = client.post("/api/reset", json={})

    assert res.status_code == 422
    service.schedule_reset.assert_not_awaited()


def test_returns_422_when_password_blank():
    service = MagicMock()
    service.schedule_reset = AsyncMock()
    _override_with(service)

    with TestClient(app) as client:
        res = client.post("/api/reset", json={"password": ""})

    assert res.status_code == 422
    service.schedule_reset.assert_not_awaited()


def test_returns_422_when_password_too_long():
    """회귀: max_length=128 초과 시 422 + 서비스 미호출."""
    service = MagicMock()
    service.schedule_reset = AsyncMock()
    _override_with(service)

    with TestClient(app) as client:
        res = client.post("/api/reset", json={"password": "x" * 129})

    assert res.status_code == 422
    service.schedule_reset.assert_not_awaited()
    # 평문이 응답 어디에도 노출되지 않아야 한다 (마스킹 + ctx 치환)
    assert "x" * 100 not in res.text


def test_returns_409_when_reset_already_in_progress():
    """회귀: 진행 중 task 있을 때 409 매핑."""
    from app.exceptions import ResetAlreadyInProgressError

    service = MagicMock()
    service.schedule_reset = AsyncMock(side_effect=ResetAlreadyInProgressError())
    _override_with(service)

    with TestClient(app) as client:
        res = client.post("/api/reset", json={"password": "secret"})

    assert res.status_code == 409
    body = res.json()
    assert body["error_code"] == "RESET_ALREADY_IN_PROGRESS"
    assert body["detail"] == "Reset already in progress"
