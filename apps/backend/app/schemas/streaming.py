from typing import Any

from pydantic import BaseModel


class StreamingLatestResponse(BaseModel):
    enabled: bool
    topic: str
    latest: dict[str, Any] | None = None
    last_error: str | None = None


class StreamingBootstrapResponse(BaseModel):
    enabled: bool
    topic: str
    minutes: int
    count: int
    source: str | None = None
    rows: list[dict[str, Any]] = []
    error: str | None = None
