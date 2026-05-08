"""세션별 백그라운드 시뮬 루프.

각 세션에 대해 asyncio task 1개를 띄우고, dt_config.sim_step.dt 주기로 step을 실행한다.
실제 step 로직(lag, ML 추론, Zeldovich, 임계치)은 모두 `digital_twin.simulation.sim_step`에
위임한다. 본 모듈은 asyncio 라이프사이클과 WebSocket broadcast만 책임진다.

step 흐름:
  1. InputInjector에서 신규 입력 pull → state.target 갱신
  2. digital_twin.simulation.sim_step 호출 (DT가 lag/ML/Zeldovich 통합 처리)
  3. WebSocket broadcast
"""

import asyncio
import logging

from app.adapters.simulator import Simulator
from app.config import Settings
from app.core.input_injector import InputInjector
from app.core.state_store import StateStore
from app.core.ws_manager import WebSocketManager
from app.schemas.stream import StreamMessage
from digital_twin.simulation import (
    DEFAULT_CONFIG,
    DTConfig,
    OutputVars,
    SimulationState,
    sim_step,
)

logger = logging.getLogger(__name__)


def _override_efficiency_with_lhv(
    output: OutputVars,
    *,
    syngas_flow: float,
    lhv: float,
) -> OutputVars:
    """효율 후처리: power / (syngas_flow × LHV).

    DT 단독 호환을 위해 features.compute_efficiency가 채워둔 값을
    백엔드 sim_loop에서 LHV 기반 식으로 덮어쓴다 (단일 진실원 일원화).
    분모 0/음수 가드 + [0, 1] 클램프.
    """
    denom = syngas_flow * lhv
    if denom <= 0.0:
        return output
    eta = output.power / denom
    eta = max(0.0, min(1.0, eta))
    return OutputVars(
        nox=output.nox,
        exhaust_temp=output.exhaust_temp,
        power=output.power,
        lambda_=output.lambda_,
        efficiency=eta,
    )


class SimLoopManager:
    """세션별 sim loop task 라이프사이클 관리."""

    def __init__(
        self,
        settings: Settings,
        state_store: StateStore,
        injector: InputInjector,
        ws_manager: WebSocketManager,
        simulator: Simulator,
        dt_config: DTConfig = DEFAULT_CONFIG,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.injector = injector
        self.ws_manager = ws_manager
        self.simulator = simulator
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
        # WebSocket push 주기 = DT step 주기. 단일 진실원은 dt_config.
        dt = self.dt_config.sim_step.dt
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
        sim_step(state, self.simulator.predict, self.dt_config)

        # 3. efficiency 후처리 — `DT_ARCHITECTURE.md §10` / `BACKEND_PRD.md §11`
        # 발전 효율은 백엔드 sim_loop에서 power/(syngas_flow × LHV)로 계산하여
        # WS 메시지 `efficiency` 필드에 포함. LHV 단위 환산은 `[조사 필요]` —
        # 가안 상수로 진행 (실측 데이터 확보 후 재산정).
        state.output = _override_efficiency_with_lhv(
            state.output,
            syngas_flow=state.current.syngas_flow,
            lhv=self.settings.syngas_lhv,
        )

    def _snapshot_payload(self, state: SimulationState) -> dict:
        msg = StreamMessage(
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
            ts=state.last_updated,
        )
        return msg.model_dump(by_alias=True, mode="json")
