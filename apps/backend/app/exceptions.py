class DomainError(Exception):
    """도메인 레이어 공통 예외 베이스."""

    error_code: str = "DOMAIN_ERROR"


class SessionNotFoundError(DomainError):
    error_code = "SESSION_NOT_FOUND"


class SessionLimitExceededError(DomainError):
    error_code = "SESSION_LIMIT_EXCEEDED"


class InvalidControlInputError(DomainError):
    error_code = "INVALID_CONTROL_INPUT"


class PredictorUnavailableError(DomainError):
    error_code = "PREDICTOR_UNAVAILABLE"


class DataNotEnoughError(DomainError):
    error_code = "DATA_NOT_ENOUGH"


class DataSourceUnavailableError(DomainError):
    error_code = "DATA_SOURCE_UNAVAILABLE"


class SessionTerminatedError(DomainError):
    error_code = "SESSION_TERMINATED"


class SessionModeConflictError(DomainError):
    """sim 모드 전용 동작을 realtime 모드에서 시도했을 때."""

    error_code = "SESSION_MODE_CONFLICT"


class ResetUnavailableError(DomainError):
    """리셋 기능이 비활성화됐거나 docker socket이 가용하지 않음."""

    error_code = "RESET_UNAVAILABLE"


class InvalidResetPasswordError(DomainError):
    """리셋 비밀번호가 일치하지 않음."""

    error_code = "INVALID_RESET_PASSWORD"

    def __init__(self) -> None:
        super().__init__("Reset password does not match")


class ResetAlreadyInProgressError(DomainError):
    """이미 리셋 백그라운드 task가 진행 중인 상태에서 추가 호출 — split-brain 재시작 방지."""

    error_code = "RESET_ALREADY_IN_PROGRESS"

    def __init__(self) -> None:
        super().__init__("Reset already in progress")
