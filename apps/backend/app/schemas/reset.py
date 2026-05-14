"""Reset 엔드포인트 request/response schema."""

from typing import Literal

from pydantic import BaseModel, Field

# uvicorn body limit이 1차 방어이지만 schema 레벨에서 명시적 상한을 두어
# 대용량 password 입력으로 encode/메모리 폭증을 차단.
_PASSWORD_MAX_LENGTH = 128


class ResetRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=_PASSWORD_MAX_LENGTH)


class ResetResponse(BaseModel):
    status: Literal["restarting"]
    message: str
    restart_in_seconds: float
