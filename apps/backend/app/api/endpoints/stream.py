"""WebSocket 실시간 스트림 endpoint.

연결 시 sid 유효성 확인. 이후 RealtimeEngine이 broadcast하는 envelope v1 payload를 push.
spec §2.2 L215: 연결 직후 1회 즉시 snapshot push (재연결 시 화면 복원).
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stream"])


@router.websocket("/session/{sid}/stream")
async def session_stream(websocket: WebSocket, sid: str) -> None:
    sessions = websocket.app.state.sessions
    ws_manager = websocket.app.state.ws_manager
    realtime_engine = websocket.app.state.realtime_engine

    if sid not in sessions:
        await websocket.accept()
        await websocket.close(code=4404, reason="session not found")
        return

    await ws_manager.connect(sid, websocket)

    # spec §2.2 L215 — 캐시된 마지막 payload가 있으면 즉시 push
    snapshot = realtime_engine.last_payload(sid)
    if snapshot is not None:
        try:
            await websocket.send_json(snapshot)
        except Exception as exc:
            logger.warning("ws_initial_snapshot_failed sid=%s err=%s", sid, exc)

    try:
        while True:
            # 클라이언트 → 서버 메시지는 keepalive 용도로만 사용
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(sid, websocket)
