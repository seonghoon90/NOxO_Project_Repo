from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_session_service
from app.domain.simulation import SimulationState
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
        target=ControlPayload(
            **{
                "IGCC.CC.G1.ca_fqsg_cl": state.target.syngas_flow,
                "IGCC.CC.G1.NQKR3_MONITOR": state.target.n2_offset,
                "IGCC.CC.G1.csgv": state.target.igv_opening,
            }
        ),
        current=ControlPayload(
            **{
                "IGCC.CC.G1.ca_fqsg_cl": state.current.syngas_flow,
                "IGCC.CC.G1.NQKR3_MONITOR": state.current.n2_offset,
                "IGCC.CC.G1.csgv": state.current.igv_opening,
            }
        ),
        output=OutputPayload(
            nox=state.output.nox,
            co=state.output.co,
            flame_temp=state.output.flame_temp,
            power=state.output.power,
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
    """async — service.start 내부에서 asyncio.create_task를 호출하므로
    엔드포인트가 event loop 위에서 실행되어야 한다."""
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
