from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_threshold_service
from app.schemas.threshold import ThresholdResponse
from app.services.threshold_service import ThresholdService

router = APIRouter(prefix="/threshold", tags=["threshold"])


@router.get("", response_model=ThresholdResponse)
def get_threshold(
    service: Annotated[ThresholdService, Depends(get_threshold_service)],
) -> ThresholdResponse:
    t = service.get()
    return ThresholdResponse(nox_ppm_limit=t.nox_ppm_limit)
