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
import time

from app.adapters.simulator import Simulator
from app.config import Settings
from app.core.input_injector import InputInjector
from app.core.session_context import SessionContext
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
        session_contexts: dict[str, SessionContext] | None = None,  # R4 — 끝에 추가
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.injector = injector
        self.ws_manager = ws_manager
        self.simulator = simulator
        self.dt_config = dt_config
        self.session_contexts: dict[str, SessionContext] = (
            session_contexts if session_contexts is not None else {}
        )
        self._tasks: dict[str, asyncio.Task] = {}

    def _build_predict_fn(self, ctx: SessionContext | None):
        """Simulator 타입별 PredictFn 생성 (NS2 클로저 패턴).

        N-A2 (4차 보강) — 회귀 모드(`ctx is None`)에서는 simulator가 Stub(`.predict` 1-인자)이거나
        ML이라 해도 ctx 없이 호출 불가. 회귀 모드는 Stub만 허용한다는 invariant를 lifespan에서 보장.
        """
        if ctx is None:
            # 회귀 모드 — Stub.predict 사용
            return self.simulator.predict
        if hasattr(self.simulator, "predict_for_session"):
            return lambda c: self.simulator.predict_for_session(c, ctx)
        return self.simulator.predict

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
        """앱 셧다운 시 모든 활성 sim_loop task cancel + cleanup."""
        tasks = list(self._tasks.values())
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        # 안전망 — finally가 모두 실행됐으면 이미 비어있음
        self.session_contexts.clear()
        self._tasks.clear()

    async def _run(self, sid: str) -> None:
        """sim_loop 본체. finally에서 ctx + state_store cleanup."""
        from app.exceptions import SessionTerminatedError

        dt = self.dt_config.sim_step.dt
        try:
            while True:
                state = self.state_store.get(sid)
                if state is None:
                    break
                try:
                    self._step(state)
                except KeyError as e:
                    logger.error("sim_loop_key_error sid=%s err=%s", sid, e)
                    break
                except SessionTerminatedError as e:
                    logger.error("session_terminated sid=%s reason=%s", sid, e)
                    await self.ws_manager.broadcast(sid, {
                        "type": "error",
                        "reason": "ml_failure_threshold",
                        "detail": str(e),
                    })
                    break
                # R10 — 기존 `_snapshot_payload` 헬퍼 유지 (sim_loop.py:138)
                await self.ws_manager.broadcast(sid, self._snapshot_payload(state))
                await asyncio.sleep(dt)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("sim_loop_crashed sid=%s err=%s", sid, exc)
        finally:
            # Z4 정책: state_store.remove / session_contexts.pop / injector.discard / ws_manager.drop_session
            # 모두 idempotent. 정상 종료 시 SessionService.stop()이 동일 cleanup을 호출하므로 중복되나 안전.
            # 비정상 종료(ML 5회 실패 등) 시 service.stop이 호출되지 않을 수 있으므로 finally에서
            # cleanup하는 게 invariant 보장에 필수.
            # WARN: 응답 직전 state 삭제로 동일 sid 재진입 시 404 — 정상 동작 (세션은 1회용).
            #
            # N-A3 (4차 보강) — 비정상 종료 경로에서도 injector queue / WS connection 누수 방지.
            # ws_manager.drop_session은 await 필요 (AsyncMock 또는 실제 async impl).
            #
            # A2 (5차 보강) — task.cancel() → CancelledError가 finally 내부 await로 재차 던져질 수 있음.
            # `except Exception`은 BaseException 인 CancelledError를 잡지 못하므로 `_tasks.pop`이 스킵되어
            # SimLoopManager._tasks dict에 dead task 누적(메모리 leak). 따라서:
            #   1) _tasks.pop을 가장 먼저 실행 (state 정리는 await 이전에 완료)
            #   2) await 호출은 (Exception, asyncio.CancelledError) 둘 다 포착하여 누수 방지
            self._tasks.pop(sid, None)
            self.session_contexts.pop(sid, None)
            self.state_store.remove(sid)
            try:
                self.injector.discard(sid)
            except Exception:
                logger.exception("injector_discard_failed sid=%s", sid)
            try:
                await self.ws_manager.drop_session(sid)
            except (Exception, asyncio.CancelledError):
                logger.exception("ws_drop_session_failed sid=%s", sid)

    def _step(self, state: SimulationState) -> None:
        from app.domain.tags import control_vars_to_tag_dict

        # N-A2 (4차 보강) — 회귀 모드에서는 session_contexts에 entry가 없을 수 있다.
        # KeyError 대신 .get()으로 안전 조회하고, ctx=None인 경로는 Stub 호출만 수행.
        ctx = self.session_contexts.get(state.sid)

        # [1] 사용자 입력 consume (가이드 §6 내부 처리 순서 1번)
        new_target = self.injector.consume(state.sid)
        if new_target is not None:
            state.target = new_target
            if ctx is not None:
                ctx.pending_input_flag = True
                ctx.last_input_t = time.monotonic()

        # [2] DT sim_step — 클로저로 ctx 바인딩 (ctx=None이면 Stub.predict 사용)
        predict_fn = self._build_predict_fn(ctx)
        sim_step(state, predict_fn, self.dt_config)

        # [3] recent_df ring-buffer 갱신 (제어 10개만 push) — ML 모드에서만
        if ctx is not None:
            ctx.push_step_row(control_vars_to_tag_dict(state.current))

        # [4] efficiency 후처리 — `DT_ARCHITECTURE.md §10` / `BACKEND_PRD.md §11`
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
