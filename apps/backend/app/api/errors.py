"""도메인 예외 → HTTP 응답 변환."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions import (
    DomainError,
    DataNotEnoughError,
    DataSourceUnavailableError,
    InvalidControlInputError,
    InvalidResetPasswordError,
    PredictorUnavailableError,
    ResetAlreadyInProgressError,
    ResetUnavailableError,
    SessionLimitExceededError,
    SessionModeConflictError,
    SessionNotFoundError,
)


_STATUS_MAP: dict[type[DomainError], int] = {
    SessionNotFoundError: 404,
    SessionLimitExceededError: 429,
    InvalidControlInputError: 400,
    PredictorUnavailableError: 503,
    DataNotEnoughError: 503,
    DataSourceUnavailableError: 503,
    SessionModeConflictError: 409,
    ResetUnavailableError: 503,
    InvalidResetPasswordError: 401,
    ResetAlreadyInProgressError: 409,
}

_SENSITIVE_FIELDS: frozenset[str] = frozenset({"password"})


def _mask_validation_errors(errors: list[dict]) -> list[dict]:
    # Pydantic v2 RequestValidationError는 errors[*].input에 원본 값을 포함한다.
    # password 등 민감 필드는 평문 노출 위험이 있어 마스킹 후 응답.
    masked: list[dict] = []
    for err in errors:
        loc = err.get("loc", ())
        is_sensitive = any(part in _SENSITIVE_FIELDS for part in loc if isinstance(part, str))
        if is_sensitive and "input" in err:
            err = {**err, "input": "***"}
        masked.append(err)
    return masked


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        status = _STATUS_MAP.get(type(exc), 400)
        return JSONResponse(
            status_code=status,
            content={"detail": str(exc) or exc.error_code, "error_code": exc.error_code},
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": _mask_validation_errors(list(exc.errors()))},
        )
