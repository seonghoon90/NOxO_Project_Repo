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
