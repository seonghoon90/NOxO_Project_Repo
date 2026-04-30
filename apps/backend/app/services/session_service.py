"""세션 라이프사이클 비즈니스 로직."""

import logging
import uuid

from app.config import Settings
from app.core.input_injector import InputInjector
from app.core.sim_loop import SimLoopManager
from app.core.state_store import StateStore
from app.core.ws_manager import WebSocketManager
from app.domain.tags import DEFAULT_CONTROL_BOUNDS, validate_control
from digital_twin.simulation import ControlVars, SimulationState
from app.exceptions import (
    InvalidControlInputError,
    SessionLimitExceededError,
    SessionNotFoundError,
)

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(
        self,
        settings: Settings,
        state_store: StateStore,
        injector: InputInjector,
        sim_loop: SimLoopManager,
        ws_manager: WebSocketManager,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.injector = injector
        self.sim_loop = sim_loop
        self.ws_manager = ws_manager

    def start(self, initial: ControlVars | None = None) -> SimulationState:
        if len(self.state_store) >= self.settings.sim_max_sessions:
            raise SessionLimitExceededError(
                f"max sessions reached ({self.settings.sim_max_sessions})"
            )

        if initial is not None:
            errors = validate_control(initial, DEFAULT_CONTROL_BOUNDS)
            if errors:
                raise InvalidControlInputError("; ".join(errors))

        sid = str(uuid.uuid4())
        state = SimulationState(sid=sid)
        if initial is not None:
            state.target = initial
            state.current = initial
        self.state_store.put(state)
        self.sim_loop.start(sid)
        return state

    def get(self, sid: str) -> SimulationState:
        state = self.state_store.get(sid)
        if state is None:
            raise SessionNotFoundError(sid)
        return state

    def submit_control(self, sid: str, controls: ControlVars) -> None:
        if sid not in self.state_store:
            raise SessionNotFoundError(sid)
        errors = validate_control(controls, DEFAULT_CONTROL_BOUNDS)
        if errors:
            raise InvalidControlInputError("; ".join(errors))
        self.injector.submit(sid, controls)

    async def stop(self, sid: str) -> None:
        if sid not in self.state_store:
            # 이미 정리된 세션이어도 남은 task/ws/input이 있을 수 있어 cleanup은 끝까지 수행한다.
            logger.debug("stop on missing sid=%s; continuing best-effort cleanup", sid)
        await self.sim_loop.stop(sid)
        self.injector.discard(sid)
        self.state_store.remove(sid)
        await self.ws_manager.drop_session(sid)
