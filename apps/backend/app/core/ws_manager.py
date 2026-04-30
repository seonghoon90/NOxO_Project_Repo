"""WebSocket 연결 매니저.

세션(sid)별로 다수의 WebSocket 구독자를 관리하고 broadcast를 수행.
연결 끊김은 send 시 예외로 감지되며, 매니저가 자동으로 정리한다.
"""

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, sid: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._subscribers.setdefault(sid, set()).add(ws)
        logger.info("WS connected sid=%s subs=%d", sid, len(self._subscribers[sid]))

    async def disconnect(self, sid: str, ws: WebSocket) -> None:
        async with self._lock:
            subs = self._subscribers.get(sid)
            if subs and ws in subs:
                subs.remove(ws)
                if not subs:
                    self._subscribers.pop(sid, None)
        logger.info("WS disconnected sid=%s", sid)

    async def broadcast(self, sid: str, payload: dict[str, Any]) -> None:
        # 스냅샷으로 복사하여 broadcast 중 mutation 영향 최소화
        async with self._lock:
            subs = list(self._subscribers.get(sid, ()))
        if not subs:
            return
        dead: list[WebSocket] = []
        for ws in subs:
            try:
                await ws.send_json(payload)
            except Exception as exc:
                logger.warning("WS send failed sid=%s err=%s", sid, exc)
                dead.append(ws)
        if dead:
            async with self._lock:
                subs_set = self._subscribers.get(sid)
                if subs_set:
                    for ws in dead:
                        subs_set.discard(ws)
                    if not subs_set:
                        self._subscribers.pop(sid, None)

    async def drop_session(self, sid: str) -> None:
        """세션 종료 시 구독자 일괄 정리."""
        async with self._lock:
            subs = self._subscribers.pop(sid, set())
        for ws in subs:
            try:
                await ws.close()
            except Exception:
                pass
