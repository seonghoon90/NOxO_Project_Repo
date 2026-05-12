"""세션 라이프사이클 비즈니스 로직."""

import logging
import uuid
from datetime import datetime, timezone

from app.config import Settings
from app.core.input_injector import InputInjector
from app.core.ml_mode import is_ml_mode_ready
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
        # 신규 인자 — 기존 시그니처 끝에 추가 (회귀 방어, R4)
        data_source=None,
        simulator=None,
        session_contexts: dict | None = None,
        simulation_log_repo=None,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.injector = injector
        self.sim_loop = sim_loop
        self.ws_manager = ws_manager
        # 신규
        self.data_source = data_source
        self.simulator = simulator
        self.session_contexts = session_contexts if session_contexts is not None else {}
        self.simulation_log_repo = simulation_log_repo

    def is_ml_mode(self) -> bool:
        """ML 모드 여부. data_source + 실제 ML simulator가 모두 준비돼야 한다."""
        return is_ml_mode_ready(self.data_source, self.simulator)

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
        self._create_session_log(sid)
        self._create_input_log(sid, state.target)
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
        self._create_input_log(sid, controls)

    async def create_session(self, sid: str) -> SimulationState:
        """B안 ML 모드 세션 생성. snapshot pull + ctx + 초기 ML 호출 + 재시도."""
        import asyncio
        from app.core.session_context import SessionContext
        from app.domain.tags import control_vars_from_tag_dict
        from app.exceptions import PredictorUnavailableError
        from digital_twin.simulation import create_initial_state

        if len(self.state_store) >= self.settings.sim_max_sessions:
            raise SessionLimitExceededError(
                f"max sessions reached ({self.settings.sim_max_sessions})"
            )

        # [3] 스냅샷 pull (DataNotEnoughError 전파)
        snapshot_df = await self.data_source.get_initial_snapshot(window_minutes=15)

        # [4] SessionContext + initial_controls (P2 — helper 경유)
        ctx = SessionContext.from_snapshot(sid, snapshot_df)
        initial_controls = control_vars_from_tag_dict(ctx.initial_controls)

        # [5] ML 초기 호출 — 재시도 1회 + 0.5초 backoff (U3 + §6.1)
        try:
            result = self.simulator.predict_for_session(initial_controls, ctx)
        except Exception as first_err:
            logger.warning("initial_ml_failed_retrying sid=%s err=%s", sid, first_err)
            await asyncio.sleep(0.5)
            try:
                result = self.simulator.predict_for_session(initial_controls, ctx)
            except Exception as second_err:
                raise PredictorUnavailableError(
                    f"initial_ml_failed sid={sid}: {second_err}"
                ) from second_err

        # [6] SimulationState 생성 — R1: create_initial_state는 predict_fn 필수
        # 초기 ML 호출 결과가 이미 ctx.cached_output_target에 들어있으므로
        # predict_fn을 cached를 반환하는 람다로 고정해 중복 호출을 회피한다.
        # 실제 MLSimulator는 ctx mutate + OutputVars 반환을 둘 다 수행하지만,
        # 방어적으로 둘 중 하나만 충족돼도 진행 가능하도록 fallback 처리한다.
        cached = ctx.cached_output_target or result
        state = create_initial_state(
            sid,
            initial_controls,
            predict_fn=lambda controls: cached,
            config=self.sim_loop.dt_config,
        )

        # [7] commit — session_contexts + state_store 동시 등록 + sim_loop start
        self.session_contexts[sid] = ctx
        self.state_store.put(state)
        self.sim_loop.start(sid)
        self._create_session_log(sid)
        self._create_input_log(sid, state.target)
        return state

    async def stop(self, sid: str) -> None:
        if sid not in self.state_store:
            # 이미 정리된 세션이어도 남은 task/ws/input이 있을 수 있어 cleanup은 끝까지 수행한다.
            logger.debug("stop on missing sid=%s; continuing best-effort cleanup", sid)
        self._finish_session_log(sid)
        await self.sim_loop.stop(sid)
        self.injector.discard(sid)
        self.session_contexts.pop(sid, None)
        self.state_store.remove(sid)
        await self.ws_manager.drop_session(sid)

    def _create_session_log(self, sid: str) -> None:
        if self.simulation_log_repo is None:
            return
        try:
            self.simulation_log_repo.create_session_log(
                sid,
                started_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        except Exception as exc:
            logger.warning("simulation_session_log_failed sid=%s err=%s", sid, exc)

    def _create_input_log(self, sid: str, controls: ControlVars) -> None:
        if self.simulation_log_repo is None:
            return
        try:
            self.simulation_log_repo.create_input_log(
                sid,
                controls,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        except Exception as exc:
            logger.warning("simulation_input_log_failed sid=%s err=%s", sid, exc)

    def _finish_session_log(self, sid: str) -> None:
        if self.simulation_log_repo is None:
            return
        try:
            self.simulation_log_repo.finish_session_log(
                sid,
                ended_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        except Exception as exc:
            logger.warning("simulation_session_finish_failed sid=%s err=%s", sid, exc)
