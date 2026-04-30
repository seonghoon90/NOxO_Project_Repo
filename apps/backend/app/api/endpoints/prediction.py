from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_prediction_service
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/prediction", tags=["prediction"])


@router.post("", response_model=PredictionResponse)
def predict(
    body: PredictionRequest,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    sid: Annotated[str | None, Query(description="활성 세션 sid (있으면 그 target 기반)")] = None,
) -> PredictionResponse:
    return service.predict(target_minutes=body.target_minutes, sid=sid)
