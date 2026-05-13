"""세션 라이프사이클 + 모드/override 정책."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from app.adapters.simulator import Simulator
from app.config import Settings
from app.core.sensor_buffer import SensorBuffer
from app.core.session import Session
from app.core.session_context import SessionContext
from app.core.ws_manager import WebSocketManager
from app.domain.tags import DEFAULT_CONTROL_BOUNDS, validate_control
from app.exceptions import (
    DataNotEnoughError,
    InvalidControlInputError,
    SessionLimitExceededError,
    SessionNotFoundError,
    SessionTerminatedError,
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
        simulator: Simulator | None = None,
        realtime_engine=None,
        simulation_log_repo=None,
    ) -> None:
        self.settings = settings
        self.sessions = sessions
        self.sensor_buffer = sensor_buffer
        self.ws_manager = ws_manager
        self.simulator = simulator
        self.realtime_engine = realtime_engine
        self.simulation_log_repo = simulation_log_repo

    def start(self) -> Session:
        """새 세션 생성 (mode='sim' default).

        initial_condition은 deprecated — 기본 운전점 + Kafka 추종으로 시작.
        세션 생성 직후 simulator로 첫 ML 호출을 강제해 cached_output_target을
        충전한다 (RealtimeEngine 첫 tick이 cache_invariant 가드를 통과해야 하므로).
        """
        if len(self.sessions) >= self.settings.sim_max_sessions:
            raise SessionLimitExceededError(
                f"max sessions reached ({self.settings.sim_max_sessions})"
            )
        sid = str(uuid.uuid4())
        try:
            ctx = SessionContext.from_sensor_buffer(sid, self.sensor_buffer)
        except ValueError as exc:
            raise DataNotEnoughError(
                f"SensorBuffer empty — bootstrap unavailable ({exc})"
            ) from exc
        now = datetime.now(timezone.utc)
        session = Session(
            sid=sid, context=ctx, created_at=now, last_active_at=now,
        )
        self._warmup_simulator_cache(session)
        self.sessions[sid] = session
        self._create_session_log(sid)
        return session

    def _warmup_simulator_cache(self, session: Session) -> None:
        """세션 생성 직후 simulator를 한 번 호출해 cached_output_target을 충전.

        ML 게이트(interval 60s)가 첫 tick에서 False여도 RealtimeEngine이 cached값을
        반환할 수 있도록 invariant를 만족시킨다. simulator 미주입 시(테스트 환경)는 skip.
        """
        if self.simulator is None:
            return
        initial_controls = ControlVars(
            syngas_flow=session.context.initial_controls.get(
                "IGCC.CC.G1.ca_fqsg_cl", 1500.0
            ),
            igv_opening=session.context.initial_controls.get(
                "IGCC.CC.G1.csgv", 75.0
            ),
            n2_offset=session.context.initial_controls.get(
                "IGCC.CC.G1.NQKR3_MONITOR", 200.0
            ),
            n2_valve_1=session.context.initial_controls.get(
                "IGCC.CC.G1.nicvs1", 50.0
            ),
            syngas_srv=session.context.initial_controls.get(
                "IGCC.CC.G1.FSAGR", 60.0
            ),
            syngas_gcv_1=session.context.initial_controls.get(
                "IGCC.CC.G1.FSAG11", 55.0
            ),
            syngas_gcv_1a=session.context.initial_controls.get(
                "IGCC.CC.G1.FSAG11A", 55.0
            ),
            syngas_gcv_2=session.context.initial_controls.get(
                "IGCC.CC.G1.FSAG12", 55.0
            ),
            ibh_valve=session.context.initial_controls.get(
                "IGCC.CC.G1.CSBHX", 30.0
            ),
            n2_flow=session.context.initial_controls.get(
                "IGCC.CC.G1.NQJ", 100.0
            ),
        )
        # ML 게이트 우회 — interval 강제 통과
        session.context.pending_input_flag = True
        try:
            self.simulator.predict_for_session(initial_controls, session.context)
        except SessionTerminatedError as exc:
            logger.warning("warmup_failed sid=%s err=%s", session.sid, exc)
        finally:
            session.context.pending_input_flag = False

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
        if self.realtime_engine is not None:
            self.realtime_engine.discard_session(sid)
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
