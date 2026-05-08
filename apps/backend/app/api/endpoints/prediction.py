from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_forecast_service
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.services.forecast_service import ForecastService

router = APIRouter(prefix="/prediction", tags=["prediction"])


@router.post("", response_model=PredictionResponse)
def predict(
    body: PredictionRequest,
    service: Annotated[ForecastService, Depends(get_forecast_service)],
) -> PredictionResponse:
    """5분 후 NOx 단발 예측 — `BACKEND_ARCHITECTURE.md §7` (horizon 5분 고정).

    body는 `{}` 또는 `{"sid": "..."}` (활성 세션 기반 예측 시).
    """
    return service.predict(sid=body.sid)
