"""WebSocket 실시간 스트림 endpoint.

연결 시 sid 유효성 확인. 이후 RealtimeEngine이 broadcast하는 envelope v1 payload를 push.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["stream"])


@router.websocket("/session/{sid}/stream")
async def session_stream(websocket: WebSocket, sid: str) -> None:
    sessions = websocket.app.state.sessions
    ws_manager = websocket.app.state.ws_manager

    if sid not in sessions:
        await websocket.accept()
        await websocket.close(code=4404, reason="session not found")
        return

    await ws_manager.connect(sid, websocket)

    try:
        while True:
            # 클라이언트 → 서버 메시지는 keepalive 용도로만 사용
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(sid, websocket)
