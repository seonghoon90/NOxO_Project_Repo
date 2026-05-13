"""세션 관리 + 모드/override 엔드포인트 (spec §2.1)."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_realtime_engine, get_session_service
from app.core.session import Session
from app.exceptions import SessionLimitExceededError, SessionNotFoundError
from app.schemas.session import (
    ControlPayload,
    SessionInfoResponse,
    SessionModeRequest,
    SessionModeResponse,
    SessionResetResponse,
    SessionStartResponse,
)
from app.services.session_service import SessionService

router = APIRouter(prefix="/session", tags=["session"])

SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
RealtimeEngineDep = Annotated[object, Depends(get_realtime_engine)]


def _serialize_override(session: Session) -> ControlPayload | None:
    if session.control_override is None:
        return None
    return ControlPayload.from_controlvars(session.control_override)


@router.post("/start", response_model=SessionStartResponse)
def start_session(
    service: SessionServiceDep,
    body: dict | None = None,
) -> SessionStartResponse:
    """세션 생성. initial_condition은 deprecated (무시)."""
    try:
        session = service.start()
    except SessionLimitExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return SessionStartResponse(
        sid=session.sid,
        mode=session.mode,
        control_override=_serialize_override(session),
        created_at=session.created_at,
    )


@router.get("/{sid}", response_model=SessionInfoResponse)
def get_session(
    sid: str,
    service: SessionServiceDep,
) -> SessionInfoResponse:
    try:
        session = service.get(sid)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SessionInfoResponse(
        sid=session.sid,
        mode=session.mode,
        control_override=_serialize_override(session),
        created_at=session.created_at,
        last_active_at=session.last_active_at,
    )


@router.get("/{sid}/snapshot")
def get_session_snapshot(
    sid: str,
    service: SessionServiceDep,
    realtime_engine: RealtimeEngineDep,
) -> dict:
    """프론트 WebSocket 재연결용 마지막 payload snapshot."""
    try:
        service.get(sid)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    payload = realtime_engine.last_payload(sid)
    if payload is None:
        raise HTTPException(status_code=404, detail="snapshot not available yet")

    outputs = dict(payload["current"]["outputs"])
    if payload.get("forecast") is not None:
        outputs["predicted_nox"] = payload["forecast"]["predicted_nox"]

    return {
        "sid": sid,
        "t": payload["tick"],
        "current": payload["current"]["controls"],
        "output": outputs,
        "warning": payload.get("warning") is not None,
        "last_updated": payload["ts"],
    }


@router.post("/{sid}/mode", response_model=SessionModeResponse)
def set_mode(
    sid: str,
    body: SessionModeRequest,
    service: SessionServiceDep,
) -> SessionModeResponse:
    try:
        session = service.set_mode(sid, body.mode)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SessionModeResponse(
        sid=session.sid,
        mode=session.mode,
        control_override=_serialize_override(session),
        changed_at=datetime.now(timezone.utc),
    )


@router.post("/{sid}/reset", response_model=SessionResetResponse)
def reset_override(
    sid: str,
    service: SessionServiceDep,
) -> SessionResetResponse:
    try:
        session = service.reset_override(sid)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SessionResetResponse(
        sid=session.sid,
        control_override=_serialize_override(session),
        reset_at=datetime.now(timezone.utc),
    )


@router.post("/{sid}/control")
def submit_control(
    sid: str,
    payload: ControlPayload,
    service: SessionServiceDep,
) -> dict:
    """제어 입력 (sim 모드 전용; realtime이면 SessionModeConflictError → 409)."""
    try:
        service.submit_control(sid, payload.to_domain())
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "control_override_set": True}


@router.post("/{sid}/stop")
async def stop_session(
    sid: str,
    service: SessionServiceDep,
) -> dict:
    await service.stop(sid)
    return {"ok": True}
