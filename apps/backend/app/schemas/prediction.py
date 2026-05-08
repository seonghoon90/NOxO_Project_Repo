from datetime import datetime

from pydantic import BaseModel


class PredictionRequest(BaseModel):
    """5분 horizon 단발 NOx 예측 요청.

    `BACKEND_ARCHITECTURE.md §7` — horizon은 5분 고정이므로 body 필드는 sid만.
    sid 미전달 시 기준 운전점 기반 예측.
    """

    sid: str | None = None


class PredictionResponse(BaseModel):
    predicted_nox: float
    target_time: datetime
    threshold_exceeded: bool
    threshold_value: float
