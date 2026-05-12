from typing import Any

from pydantic import BaseModel


class StreamingLatestResponse(BaseModel):
    enabled: bool
    topic: str
    latest: dict[str, Any] | None = None
    last_error: str | None = None
