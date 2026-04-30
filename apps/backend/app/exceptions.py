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
