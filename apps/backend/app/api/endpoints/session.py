import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_session_service
from app.domain.tags import control_vars_to_tag_dict
from digital_twin.simulation import SimulationState
from app.schemas.common import AckResponse
from app.schemas.session import (
    ControlPayload,
    OutputPayload,
    SnapshotResponse,
    StartSessionRequest,
    StartSessionResponse,
)
from app.services.session_service import SessionService

router = APIRouter(prefix="/session", tags=["session"])

SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]


def _to_snapshot(state: SimulationState) -> SnapshotResponse:
    return SnapshotResponse(
        sid=state.sid,
        t=round(state.t, 3),
        target=ControlPayload(**control_vars_to_tag_dict(state.target)),
        current=ControlPayload(**control_vars_to_tag_dict(state.current)),
        output=OutputPayload(
            nox=state.output.nox,
            exhaust_temp=state.output.exhaust_temp,
            power=state.output.power,
            efficiency=state.output.efficiency,
            **{"lambda": state.output.lambda_},
        ),
        warning=state.warning,
        last_updated=state.last_updated,
    )


@router.post("/start", response_model=StartSessionResponse)
async def start_session(
    body: StartSessionRequest,
    service: SessionServiceDep,
) -> StartSessionResponse:
    """B안 ML 모드 / Stub 회귀 모드 분기."""
    if service.is_ml_mode():
        sid = str(uuid.uuid4())
        state = await service.create_session(sid)
    else:
        initial = body.initial_condition.to_domain() if body.initial_condition else None
        state = service.start(initial)
    return StartSessionResponse(sid=state.sid, snapshot=_to_snapshot(state))


@router.post("/{sid}/control", response_model=AckResponse)
async def submit_control(
    sid: str,
    payload: ControlPayload,
    service: SessionServiceDep,
) -> AckResponse:
    service.submit_control(sid, payload.to_domain())
    return AckResponse()


@router.post("/{sid}/stop", response_model=AckResponse)
async def stop_session(sid: str, service: SessionServiceDep) -> AckResponse:
    await service.stop(sid)
    return AckResponse()


@router.get("/{sid}/snapshot", response_model=SnapshotResponse)
async def get_snapshot(sid: str, service: SessionServiceDep) -> SnapshotResponse:
    return _to_snapshot(service.get(sid))
