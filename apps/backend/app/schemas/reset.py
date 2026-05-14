"""Reset 엔드포인트 request/response schema."""

from typing import Literal

from pydantic import BaseModel, Field


class ResetRequest(BaseModel):
    password: str = Field(..., min_length=1)


class ResetResponse(BaseModel):
    status: Literal["restarting"]
    message: str
    restart_in_seconds: float
