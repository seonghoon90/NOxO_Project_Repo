"""Reset request/response schema 단위 테스트."""

import pytest
from pydantic import ValidationError

from app.schemas.reset import ResetRequest, ResetResponse


def test_reset_request_accepts_non_empty_password():
    req = ResetRequest(password="my-secret")
    assert req.password == "my-secret"


def test_reset_request_rejects_empty_password():
    with pytest.raises(ValidationError):
        ResetRequest(password="")


def test_reset_request_rejects_missing_password():
    with pytest.raises(ValidationError):
        ResetRequest()  # type: ignore[call-arg]


def test_reset_response_status_literal_and_fields():
    res = ResetResponse(
        status="restarting",
        message="Backend and producer will restart shortly",
        restart_in_seconds=2.0,
    )
    dumped = res.model_dump()
    assert dumped == {
        "status": "restarting",
        "message": "Backend and producer will restart shortly",
        "restart_in_seconds": 2.0,
    }


def test_reset_response_rejects_other_status():
    with pytest.raises(ValidationError):
        ResetResponse(status="ok", message="x", restart_in_seconds=1.0)  # type: ignore[arg-type]
