"""모든 endpoint 라우터를 단일 APIRouter로 묶음.

추후 버저닝이 필요해지면 본 모듈을 `api/v1/router.py`로 옮기고 prefix만 추가하면 됨.
"""

from fastapi import APIRouter

from app.api.endpoints import (
    health,
    prediction,
    session,
    stream,
    streaming,
    threshold,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(session.router)
api_router.include_router(stream.router)
api_router.include_router(streaming.router)
api_router.include_router(prediction.router)
api_router.include_router(threshold.router)
