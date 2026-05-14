"""ResetUnavailable/InvalidResetPassword/AlreadyInProgress 예외 → HTTP 매핑 테스트."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.api.errors import register_exception_handlers
from app.exceptions import (
    InvalidResetPasswordError,
    ResetAlreadyInProgressError,
    ResetUnavailableError,
)


class _PasswordPayload(BaseModel):
    password: str = Field(..., min_length=1)


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise-unavailable")
    def _raise_unavailable():
        raise ResetUnavailableError("docker socket missing")

    @app.get("/raise-invalid-pw")
    def _raise_invalid_pw():
        raise InvalidResetPasswordError()

    @app.get("/raise-already")
    def _raise_already():
        raise ResetAlreadyInProgressError()

    @app.post("/echo-password")
    def _echo_password(payload: _PasswordPayload):
        return {"ok": True}

    return app


def test_reset_unavailable_returns_503_with_error_code():
    client = TestClient(_build_app())
    res = client.get("/raise-unavailable")
    assert res.status_code == 503
    body = res.json()
    assert body["detail"] == "docker socket missing"
    assert body["error_code"] == "RESET_UNAVAILABLE"


def test_invalid_reset_password_returns_401_with_error_code():
    client = TestClient(_build_app())
    res = client.get("/raise-invalid-pw")
    assert res.status_code == 401
    body = res.json()
    assert body["detail"] == "Reset password does not match"
    assert body["error_code"] == "INVALID_RESET_PASSWORD"


def test_reset_already_in_progress_returns_409_with_error_code():
    """회귀: concurrent reset 시 409 매핑."""
    client = TestClient(_build_app())
    res = client.get("/raise-already")
    assert res.status_code == 409
    body = res.json()
    assert body["detail"] == "Reset already in progress"
    assert body["error_code"] == "RESET_ALREADY_IN_PROGRESS"


def test_validation_error_masks_password_input():
    """회귀: 422 응답의 errors[*].input에서 password 필드는 *** 로 마스킹."""
    client = TestClient(_build_app())
    # 타입 confusion으로 422 유발 — Pydantic v2 기본 errors는 input을 포함
    res = client.post("/echo-password", json={"password": "leak-me-please"})
    # min_length=1 통과 (정상)이므로 200
    assert res.status_code == 200

    # 빈 문자열로 422 유도
    res2 = client.post("/echo-password", json={"password": ""})
    assert res2.status_code == 422
    body = res2.json()
    # detail은 errors 리스트
    assert isinstance(body["detail"], list)
    for err in body["detail"]:
        if "password" in err.get("loc", []):
            # 평문이 절대 노출되어선 안 된다
            assert err.get("input") in ("***", None) or "leak-me" not in str(err.get("input", ""))


def test_validation_error_password_missing_no_input_leak():
    """회귀: password 필드 자체 누락 시에도 응답에 평문 leak 없음."""
    client = TestClient(_build_app())
    res = client.post("/echo-password", json={"password": "supersecret-original"})
    assert res.status_code == 200
    # 다른 필드 confusion
    res2 = client.post("/echo-password", json={"wrong_field": "x"})
    assert res2.status_code == 422
    body_text = res2.text
    assert "supersecret-original" not in body_text


def test_validation_error_masks_token_and_secret_fields():
    """회귀: password 외 token/secret/api_key 화이트리스트 필드도 마스킹."""
    from pydantic import BaseModel, Field as PField

    class _MultiSecretPayload(BaseModel):
        token: str = PField(..., min_length=10)
        api_key: str = PField(..., min_length=10)

    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/multi-secret")
    def _ep(payload: _MultiSecretPayload):
        return {"ok": True}

    client = TestClient(app)
    res = client.post("/multi-secret", json={"token": "x", "api_key": "y"})
    assert res.status_code == 422
    body_text = res.text
    # 평문 누출 없음
    assert '"input":"x"' not in body_text
    assert '"input":"y"' not in body_text
    # 마스킹 또는 ctx 치환 확인
    body = res.json()
    for err in body["detail"]:
        loc = err.get("loc", [])
        if "token" in loc or "api_key" in loc:
            assert err.get("input") in ("***", None)
            if "ctx" in err:
                assert err["ctx"] == {"masked": True}


def test_validation_error_preserves_non_sensitive_field_input():
    """회귀: 마스킹 화이트리스트 외 필드는 input이 보존된다 (개발자 디버깅 가시성)."""
    from pydantic import BaseModel, Field as PField

    class _NormalPayload(BaseModel):
        username: str = PField(..., min_length=3)

    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/normal")
    def _ep(payload: _NormalPayload):
        return {"ok": True}

    client = TestClient(app)
    res = client.post("/normal", json={"username": "ab"})
    assert res.status_code == 422
    body = res.json()
    found_input = False
    for err in body["detail"]:
        if "username" in err.get("loc", []):
            assert err.get("input") == "ab"
            found_input = True
    assert found_input
