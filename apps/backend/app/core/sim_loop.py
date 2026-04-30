"""세션별 백그라운드 시뮬 루프.

각 세션에 대해 asyncio task 1개를 띄우고, sim_dt_seconds 주기로 step을 실행한다.
실제 step 로직(lag, ML 추론, Zeldovich, 임계치)은 모두 `digital_twin.simulation.sim_step`에
위임한다. 본 모듈은 asyncio 라이프사이클과 WebSocket broadcast만 책임진다.

step 흐름:
  1. InputInjector에서 신규 입력 pull → state.target 갱신
  2. digital_twin.simulation.sim_step 호출 (DT가 lag/ML/Zeldovich 통합 처리)
  3. WebSocket broadcast
"""

import asyncio
import logging

from app.adapters.predictor import Predictor
from app.config import Settings
from app.core.input_injector import InputInjector
from app.core.state_store import StateStore
from app.core.ws_manager import WebSocketManager
from app.schemas.stream import StreamMessage
from digital_twin.simulation import (
    DEFAULT_CONFIG,
    DTConfig,
    SimulationState,
    sim_step,
)

logger = logging.getLogger(__name__)


class SimLoopManager:
    """세션별 sim loop task 라이프사이클 관리."""

    def __init__(
        self,
        settings: Settings,
        state_store: StateStore,
        injector: InputInjector,
        ws_manager: WebSocketManager,
        predictor: Predictor,
        dt_config: DTConfig = DEFAULT_CONFIG,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.injector = injector
        self.ws_manager = ws_manager
        self.predictor = predictor
        self.dt_config = dt_config
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
        # 백엔드 settings의 dt(WebSocket push 주기)를 DT 설정과 일치시킨다.
        # 향후 P1-4에서 settings의 sim_dt_seconds를 DT config로 위임하면 본 라인 제거.
        dt = self.settings.sim_dt_seconds
        try:
            while True:
                state = self.state_store.get(sid)
                if state is None:
                    break
                self._step(state)
                await self.ws_manager.broadcast(sid, self._snapshot_payload(state))
                await asyncio.sleep(dt)
        except asyncio.CancelledError:
            logger.info("sim loop cancelled sid=%s", sid)
            raise
        except Exception as exc:
            logger.exception("sim loop crashed sid=%s err=%s", sid, exc)
        finally:
            self._tasks.pop(sid, None)

    def _step(self, state: SimulationState) -> None:
        # 1. 신규 사용자 입력 반영 (가이드 §6 내부 처리 순서 1번)
        new_target = self.injector.consume(state.sid)
        if new_target is not None:
            state.target = new_target

        # 2. DT 코어에 위임 (Step 2~8: lag, ML 추론, Zeldovich, warning 갱신 모두 DT가 수행)
        sim_step(state, self.predictor.predict, self.dt_config)

    def _snapshot_payload(self, state: SimulationState) -> dict:
        msg = StreamMessage(
            sid=state.sid,
            t=round(state.t, 3),
            syngas_flow=state.current.syngas_flow,
            n2_offset=state.current.n2_offset,
            igv_opening=state.current.igv_opening,
            nox=state.output.nox,
            co=state.output.co,
            exhaust_temp=state.output.exhaust_temp,
            lambda_=state.output.lambda_,
            power=state.output.power,
            warning=state.warning,
            ts=state.last_updated,
        )
        return msg.model_dump(by_alias=True, mode="json")
