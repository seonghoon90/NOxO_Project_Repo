"""앱 헬스체크 + ml_simulator_ready 상태."""

import os

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict:
    """ml_simulator_ready = simulator.name == "ml" AND SIMULATOR_FALLBACK_STUB != "true"."""
    simulator = getattr(request.app.state, "simulator", None)
    ml_ready = (
        getattr(simulator, "name", None) == "ml"
        and os.getenv("SIMULATOR_FALLBACK_STUB", "").lower() != "true"
    )
    return {
        "status": "ok",
        "ml_simulator_ready": ml_ready,
    }
