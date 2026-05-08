"""WebSocket 스트림 엔드포인트.

연결 시 sid 유효성을 확인하고, 즉시 현재 snapshot 1회 push 후 broadcast 채널에
구독자로 등록한다. 클라이언트는 sim loop가 매 step 후 push하는 메시지를 수신한다.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.stream import StreamMessage

router = APIRouter(tags=["stream"])


@router.websocket("/session/{sid}/stream")
async def session_stream(
    websocket: WebSocket,
    sid: str,
) -> None:
    """WebSocket은 Request 기반 Depends가 동작하지 않으므로
    websocket.app.state에서 직접 컴포넌트를 꺼낸다."""
    state_store = websocket.app.state.state_store
    ws_manager = websocket.app.state.ws_manager

    if sid not in state_store:
        # accept 후 close해야 클라이언트가 사유를 받을 수 있음
        await websocket.accept()
        await websocket.close(code=4404, reason="session not found")
        return

    await ws_manager.connect(sid, websocket)

    # 초기 snapshot 1회 push (재연결 직후 즉시 화면 복원용)
    state = state_store.get(sid)
    if state is not None:
        snapshot = StreamMessage(
            sid=state.sid,
            t=round(state.t, 3),
            syngas_flow=state.current.syngas_flow,
            igv_opening=state.current.igv_opening,
            n2_offset=state.current.n2_offset,
            n2_valve_1=state.current.n2_valve_1,
            syngas_srv=state.current.syngas_srv,
            syngas_gcv_1=state.current.syngas_gcv_1,
            syngas_gcv_1a=state.current.syngas_gcv_1a,
            syngas_gcv_2=state.current.syngas_gcv_2,
            ibh_valve=state.current.ibh_valve,
            n2_flow=state.current.n2_flow,
            nox=state.output.nox,
            exhaust_temp=state.output.exhaust_temp,
            lambda_=state.output.lambda_,
            power=state.output.power,
            efficiency=state.output.efficiency,
            warning=state.warning,
            ts=state.last_updated or datetime.now(timezone.utc),
        )
        await websocket.send_json(snapshot.model_dump(by_alias=True, mode="json"))

    try:
        while True:
            # 클라이언트 → 서버 메시지는 현재 사용 안 함. 연결 유지 목적으로 receive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(sid, websocket)
