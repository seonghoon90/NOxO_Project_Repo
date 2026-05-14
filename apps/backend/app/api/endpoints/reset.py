"""POST /api/reset — backend·producer 컨테이너 재시작 트리거.

비밀번호 검증 + docker 가용성 체크 후 백그라운드 task로 재시작 예약.
실제 재시작 로직은 ResetService에 위임.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_reset_service
from app.schemas.reset import ResetRequest, ResetResponse
from app.services.reset_service import ResetService

router = APIRouter()


@router.post("/reset", response_model=ResetResponse)
async def reset(
    payload: ResetRequest,
    service: Annotated[ResetService, Depends(get_reset_service)],
) -> ResetResponse:
    return await service.schedule_reset(password=payload.password)
