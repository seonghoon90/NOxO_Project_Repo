from collections import deque
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.core.session_context import SessionContext
from app.core.sim_loop import SimLoopManager
from app.domain.tags import CONTROL_TAGS
from digital_twin.simulation import (
    DEFAULT_CONFIG, ControlVars, OutputVars, SimulationState,
)


def _make_state(sid: str = "sid1") -> SimulationState:
    controls = ControlVars(
        syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
        n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
        syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0,
    )
    return SimulationState(
        sid=sid, target=controls, current=controls,
        output_target=OutputVars(nox=20.0, exhaust_temp=580.0, power=248.6, lambda_=1.1, efficiency=0.89),
        output=OutputVars(nox=20.0, exhaust_temp=580.0, power=248.6, lambda_=1.1, efficiency=0.89),
    )


def _make_ctx(sid: str = "sid1") -> SessionContext:
    plant = {f"dist_{i}": 1.0 for i in range(29)}
    plant["IGCC.CC.G1.TTXM"] = 580.0
    return SessionContext(
        sid=sid, plant_context=plant, recent_df_buffer=deque(maxlen=900),
        initial_controls={tag: 0.0 for tag in CONTROL_TAGS},
        cached_output_target=OutputVars(nox=20.0, exhaust_temp=580.0, power=248.6, lambda_=1.1, efficiency=0.89),
    )


@pytest.fixture
def sim_loop_manager():
    from app.config import Settings
    settings = Settings()
    state_store = MagicMock()
    injector = MagicMock()
    injector.consume.return_value = None
    ws_manager = MagicMock()
    ws_manager.broadcast = AsyncMock()
    simulator = MagicMock()
    simulator.predict_for_session = MagicMock(
        return_value=OutputVars(nox=25.0, exhaust_temp=580.0, power=248.6, lambda_=1.1, efficiency=0.89)
    )
    session_contexts: dict[str, SessionContext] = {}
    # R4 — 기존 시그니처 그대로 + session_contexts 끝에 추가
    mgr = SimLoopManager(
        settings, state_store, injector, ws_manager, simulator,
        dt_config=DEFAULT_CONFIG, session_contexts=session_contexts,
    )
    return mgr, state_store, injector, simulator, session_contexts


def test_step_sets_pending_input_flag_on_new_target(sim_loop_manager, monkeypatch):
    mgr, state_store, injector, simulator, contexts = sim_loop_manager
    state = _make_state()
    ctx = _make_ctx()
    contexts["sid1"] = ctx
    new_target = ControlVars(
        syngas_flow=2000.0, igv_opening=75.0, n2_offset=200.0,
        n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
        syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0,
    )
    injector.consume.return_value = new_target
    monkeypatch.setattr("app.core.sim_loop.time.monotonic", lambda: 5.0)
    mgr._step(state)
    assert ctx.pending_input_flag is True
    assert ctx.last_input_t == 5.0


def test_step_calls_push_step_row_after_sim_step(sim_loop_manager):
    mgr, state_store, injector, simulator, contexts = sim_loop_manager
    state = _make_state()
    ctx = _make_ctx()
    contexts["sid1"] = ctx
    mgr._step(state)
    assert len(ctx.recent_df_buffer) == 1


def test_build_predict_fn_uses_closure_for_ml_simulator(sim_loop_manager):
    mgr, _, _, simulator, contexts = sim_loop_manager
    ctx = _make_ctx()
    contexts["sid1"] = ctx
    predict_fn = mgr._build_predict_fn(ctx)
    # 클로저는 ctx를 묶어 1-인자 호출
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    predict_fn(controls)
    simulator.predict_for_session.assert_called_once()
    args = simulator.predict_for_session.call_args
    assert args.args[1] is ctx
