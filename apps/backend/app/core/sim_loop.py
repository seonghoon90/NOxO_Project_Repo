"""세션별 백그라운드 시뮬 루프.

각 세션에 대해 asyncio task 1개를 띄우고, sim_dt_seconds 주기로 step을 실행한다.
step 내용:
  1. InputInjector에서 신규 입력 pull → state.target 갱신
  2. lag 모델로 current 변수 점진 수렴
  3. Predictor.predict(current) → output_target
  4. lag 모델로 output 점진 수렴
  5. WebSocket broadcast
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.adapters.predictor import Predictor
from app.config import Settings
from app.core.input_injector import InputInjector
from app.core.state_store import StateStore
from app.core.ws_manager import WebSocketManager
from app.domain.simulation import SimulationState
from app.domain.tags import ControlVars, OutputVars
from app.schemas.stream import StreamMessage

logger = logging.getLogger(__name__)


def _lag_step(current: float, target: float, dt: float, tau: float) -> float:
    """1차 lag: current += (target - current) * dt / tau"""
    if tau <= 0:
        return target
    return current + (target - current) * dt / tau


class SimLoopManager:
    """세션별 sim loop task 라이프사이클 관리."""

    def __init__(
        self,
        settings: Settings,
        state_store: StateStore,
        injector: InputInjector,
        ws_manager: WebSocketManager,
        predictor: Predictor,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.injector = injector
        self.ws_manager = ws_manager
        self.predictor = predictor
        self._tasks: dict[str, asyncio.Task] = {}

    def start(self, sid: str) -> None:
        if sid in self._tasks:
            return
        task = asyncio.create_task(self._run(sid), name=f"sim-loop:{sid}")
        self._tasks[sid] = task

    async def stop(self, sid: str) -> None:
        task = self._tasks.pop(sid, None)
        if not task:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def stop_all(self) -> None:
        sids = list(self._tasks.keys())
        for sid in sids:
            await self.stop(sid)

    async def _run(self, sid: str) -> None:
        dt = self.settings.sim_dt_seconds
        try:
            while True:
                state = self.state_store.get(sid)
                if state is None:
                    break
                self._step(state, dt)
                await self.ws_manager.broadcast(sid, self._snapshot_payload(state))
                await asyncio.sleep(dt)
        except asyncio.CancelledError:
            logger.info("sim loop cancelled sid=%s", sid)
            raise
        except Exception as exc:
            logger.exception("sim loop crashed sid=%s err=%s", sid, exc)
        finally:
            self._tasks.pop(sid, None)

    def _step(self, state: SimulationState, dt: float) -> None:
        s = self.settings

        # 1. 신규 입력 반영
        new_target = self.injector.consume(state.sid)
        if new_target is not None:
            state.target = new_target

        # 2. 제어 변수 lag 수렴
        c = state.current
        t = state.target
        state.current = ControlVars(
            syngas_flow=_lag_step(c.syngas_flow, t.syngas_flow, dt, s.tau_fuel),
            n2_offset=_lag_step(c.n2_offset, t.n2_offset, dt, s.tau_n2),
            igv_opening=_lag_step(c.igv_opening, t.igv_opening, dt, s.tau_igv),
        )

        # 3. Predictor → 정상상태 출력 target
        state.output_target = self.predictor.predict(state.current)

        # 4. 출력 lag 수렴 (변수별 시간 상수 다름)
        o = state.output
        ot = state.output_target
        state.output = OutputVars(
            nox=_lag_step(o.nox, ot.nox, dt, s.tau_nox),
            co=_lag_step(o.co, ot.co, dt, s.tau_co),
            flame_temp=_lag_step(o.flame_temp, ot.flame_temp, dt, s.tau_temp),
            lambda_=ot.lambda_,  # λ는 즉시 계산값
            power=_lag_step(o.power, ot.power, dt, s.tau_power),
        )

        # 5. 메타 갱신
        state.t += dt
        state.last_updated = datetime.now(timezone.utc)
        state.warning = state.output.nox > s.nox_threshold_ppm

    def _snapshot_payload(self, state: SimulationState) -> dict:
        msg = StreamMessage(
            sid=state.sid,
            t=round(state.t, 3),
            syngas_flow=state.current.syngas_flow,
            n2_offset=state.current.n2_offset,
            igv_opening=state.current.igv_opening,
            nox=state.output.nox,
            co=state.output.co,
            flame_temp=state.output.flame_temp,
            lambda_=state.output.lambda_,
            power=state.output.power,
            warning=state.warning,
            ts=state.last_updated,
        )
        return msg.model_dump(by_alias=True, mode="json")
