import os

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict:
    """앱 헬스체크 + ml_simulator_ready 상태 (spec §7.7.4).

    ml_simulator_ready 판정은 SessionService.is_ml_mode와 동일 기준:
    simulator.name == "ml" AND SIMULATOR_FALLBACK_STUB != "true".
    Stub 회귀 모드(Stub fallback 또는 환경변수 강제)는 false.
    """
    simulator = getattr(request.app.state, "simulator", None)
    ml_ready = (
        getattr(simulator, "name", None) == "ml"
        and os.getenv("SIMULATOR_FALLBACK_STUB", "").lower() != "true"
    )
    return {
        "status": "ok",
        "ml_simulator_ready": ml_ready,
    }
