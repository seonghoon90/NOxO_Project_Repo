"""세션 라이프사이클 + 모드/override 정책."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from app.config import Settings
from app.core.sensor_buffer import SensorBuffer
from app.core.session import Session
from app.core.session_context import SessionContext
from app.core.ws_manager import WebSocketManager
from app.domain.tags import DEFAULT_CONTROL_BOUNDS, validate_control
from app.exceptions import (
    InvalidControlInputError,
    SessionLimitExceededError,
    SessionNotFoundError,
)
from digital_twin.simulation import ControlVars

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(
        self,
        settings: Settings,
        sessions: dict[str, Session],
        sensor_buffer: SensorBuffer,
        ws_manager: WebSocketManager,
        simulation_log_repo=None,
    ) -> None:
        self.settings = settings
        self.sessions = sessions
        self.sensor_buffer = sensor_buffer
        self.ws_manager = ws_manager
        self.simulation_log_repo = simulation_log_repo

    def start(self) -> Session:
        """새 세션 생성 (mode='sim' default).

        initial_condition은 deprecated — 기본 운전점 + Kafka 추종으로 시작.
        """
        if len(self.sessions) >= self.settings.sim_max_sessions:
            raise SessionLimitExceededError(
                f"max sessions reached ({self.settings.sim_max_sessions})"
            )
        sid = str(uuid.uuid4())
        ctx = SessionContext.from_sensor_buffer(sid, self.sensor_buffer)
        now = datetime.now(timezone.utc)
        session = Session(
            sid=sid, context=ctx, created_at=now, last_active_at=now,
        )
        self.sessions[sid] = session
        self._create_session_log(sid)
        return session

    def get(self, sid: str) -> Session:
        session = self.sessions.get(sid)
        if session is None:
            raise SessionNotFoundError(sid)
        return session

    def set_mode(self, sid: str, mode: str) -> Session:
        session = self.get(sid)
        session.set_mode(mode)
        return session

    def submit_control(self, sid: str, controls: ControlVars) -> None:
        session = self.get(sid)
        errors = validate_control(controls, DEFAULT_CONTROL_BOUNDS)
        if errors:
            raise InvalidControlInputError("; ".join(errors))
        session.set_override(controls)  # realtime이면 SessionModeConflictError
        self._create_input_log(sid, controls)

    def reset_override(self, sid: str) -> Session:
        session = self.get(sid)
        session.clear_override()
        return session

    async def stop(self, sid: str) -> None:
        if sid not in self.sessions:
            logger.debug("stop on missing sid=%s; best-effort cleanup", sid)
        self._finish_session_log(sid)
        self.sessions.pop(sid, None)
        await self.ws_manager.drop_session(sid)

    # --- DB logging helpers (best-effort) ---

    def _create_session_log(self, sid: str) -> None:
        if self.simulation_log_repo is None:
            return
        try:
            self.simulation_log_repo.create_session_log(
                sid, started_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        except Exception as exc:
            logger.warning("simulation_session_log_failed sid=%s err=%s", sid, exc)

    def _create_input_log(self, sid: str, controls: ControlVars) -> None:
        if self.simulation_log_repo is None:
            return
        try:
            self.simulation_log_repo.create_input_log(
                sid, controls,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        except Exception as exc:
            logger.warning("simulation_input_log_failed sid=%s err=%s", sid, exc)

    def _finish_session_log(self, sid: str) -> None:
        if self.simulation_log_repo is None:
            return
        try:
            self.simulation_log_repo.finish_session_log(
                sid, ended_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        except Exception as exc:
            logger.warning("simulation_session_finish_failed sid=%s err=%s", sid, exc)
