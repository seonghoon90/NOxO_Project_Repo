from datetime import datetime

from pydantic import BaseModel


class PredictionRequest(BaseModel):
    target_minutes: int = 5  # 미래 시점 (분 단위)


class PredictionResponse(BaseModel):
    predicted_nox: float
    target_time: datetime
    threshold_exceeded: bool
    threshold_value: float
