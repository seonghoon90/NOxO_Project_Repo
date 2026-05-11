from collections import deque
from unittest.mock import MagicMock

import pytest

# R18 — 본 파일 후속 fixture/test에서 모두 필요
from app.adapters.simulator.ml import (
    MLSimulator, ML_INTERVAL_SEC, DEBOUNCE_SEC,
)
from app.core.session_context import SessionContext
from app.exceptions import SessionTerminatedError
from digital_twin.simulation import OutputVars


@pytest.fixture
def make_ctx():
    def _factory(**kwargs):
        defaults = dict(
            sid="t",
            plant_context={},
            recent_df_buffer=deque(maxlen=900),
            initial_controls={},
            last_ml_call_t=0.0,
            last_input_t=0.0,
            pending_input_flag=False,
        )
        defaults.update(kwargs)
        return SessionContext(**defaults)
    return _factory


@pytest.fixture
def sim(patched_models_dir):
    """패치된 더미 모델 경로로 MLSimulator 생성."""
    return MLSimulator(models_dir=patched_models_dir)


def test_should_call_ml_returns_true_after_debounce(sim, make_ctx):
    """pending=True, debounce 충족 → True + reason=input."""
    ctx = make_ctx(pending_input_flag=True, last_input_t=0.0)
    assert sim._should_call_ml(1.0, ctx) is True
    assert ctx._last_gate_reason == "input"


def test_should_call_ml_returns_true_after_interval(sim, make_ctx):
    """input 없고 60초 경과 → True + reason=interval."""
    ctx = make_ctx(last_ml_call_t=0.0, pending_input_flag=False)
    assert sim._should_call_ml(60.0, ctx) is True
    assert ctx._last_gate_reason == "interval"


def test_should_call_ml_returns_false_within_interval(sim, make_ctx):
    """input 없고 60초 미만 → False."""
    ctx = make_ctx(last_ml_call_t=0.0)
    assert sim._should_call_ml(59.999, ctx) is False


def test_should_call_ml_input_gate_takes_precedence(sim, make_ctx):
    """input + interval 둘 다 충족 시 input 우선."""
    ctx = make_ctx(pending_input_flag=True, last_input_t=0.0, last_ml_call_t=0.0)
    assert sim._should_call_ml(60.0, ctx) is True
    assert ctx._last_gate_reason == "input"


def test_should_call_ml_exact_60_seconds_boundary(sim, make_ctx):
    """fake_t == 60.0 → True (>= 비교)."""
    ctx = make_ctx(last_ml_call_t=0.0)
    assert sim._should_call_ml(60.0, ctx) is True


def test_should_call_ml_just_below_60_seconds(sim, make_ctx):
    """fake_t == 59.999 → False."""
    ctx = make_ctx(last_ml_call_t=0.0)
    assert sim._should_call_ml(59.999, ctx) is False


def test_should_call_ml_exact_1_second_debounce(sim, make_ctx):
    """debounce 정확 1.0초 → True."""
    ctx = make_ctx(pending_input_flag=True, last_input_t=0.0)
    assert sim._should_call_ml(1.0, ctx) is True


def test_should_call_ml_just_below_1_second_debounce(sim, make_ctx):
    """debounce 0.999초 → False (interval도 미충족)."""
    ctx = make_ctx(pending_input_flag=True, last_input_t=0.0, last_ml_call_t=30.0)
    assert sim._should_call_ml(0.999, ctx) is False


def test_predict_one_arg_raises_not_implemented(sim):
    """Simulator Protocol 1-인자 호출은 NotImplementedError."""
    from digital_twin.simulation import ControlVars
    with pytest.raises(NotImplementedError):
        sim.predict(ControlVars(
            syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
            n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
            syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0,
        ))


def test_build_current_row_merges_plant_context_and_controls(sim, make_ctx):
    """RAW 39 + TTXM 1 = 40컬럼 단일 행 반환."""
    from digital_twin.preprocess import RAW_FEATURES
    from digital_twin.simulation import ControlVars

    disturbance = [c for c in RAW_FEATURES if c not in __import__("app.domain.tags", fromlist=["CONTROL_TAGS"]).CONTROL_TAGS]
    plant = {k: 1.0 for k in disturbance}
    plant["IGCC.CC.G1.TTXM"] = 580.0
    ctx = make_ctx(plant_context=plant)
    controls = ControlVars(
        syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
        n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
        syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0,
    )
    df = sim._build_current_row(controls, ctx)
    assert df.shape == (1, 40)


def test_build_current_row_respects_feature_order(sim, make_ctx):
    """컬럼 순서 = RAW_FEATURES + TTXM."""
    from digital_twin.preprocess import RAW_FEATURES
    from digital_twin.simulation import ControlVars

    disturbance = [c for c in RAW_FEATURES if c not in __import__("app.domain.tags", fromlist=["CONTROL_TAGS"]).CONTROL_TAGS]
    plant = {k: 0.0 for k in disturbance}
    plant["IGCC.CC.G1.TTXM"] = 0.0
    ctx = make_ctx(plant_context=plant)
    controls = ControlVars(
        syngas_flow=0.0, igv_opening=0.0, n2_offset=0.0,
        n2_valve_1=0.0, syngas_srv=0.0, syngas_gcv_1=0.0,
        syngas_gcv_1a=0.0, syngas_gcv_2=0.0, ibh_valve=0.0, n2_flow=0.0,
    )
    df = sim._build_current_row(controls, ctx)
    expected = list(RAW_FEATURES) + ["IGCC.CC.G1.TTXM"]
    assert list(df.columns) == expected


def test_build_current_row_uses_ttxm_from_plant_context(sim, make_ctx):
    """TTXM 값은 plant_context의 freeze 값 사용."""
    from digital_twin.preprocess import RAW_FEATURES
    from digital_twin.simulation import ControlVars

    disturbance = [c for c in RAW_FEATURES if c not in __import__("app.domain.tags", fromlist=["CONTROL_TAGS"]).CONTROL_TAGS]
    plant = {k: 0.0 for k in disturbance}
    plant["IGCC.CC.G1.TTXM"] = 600.0  # freeze 값
    ctx = make_ctx(plant_context=plant)
    controls = ControlVars(
        syngas_flow=1.0, igv_opening=1.0, n2_offset=1.0,
        n2_valve_1=1.0, syngas_srv=1.0, syngas_gcv_1=1.0,
        syngas_gcv_1a=1.0, syngas_gcv_2=1.0, ibh_valve=1.0, n2_flow=1.0,
    )
    df = sim._build_current_row(controls, ctx)
    assert df["IGCC.CC.G1.TTXM"].iloc[0] == 600.0


def test_result_to_outputvars_maps_targets_correctly(sim):
    """dt_predict dict의 3 타깃 → OutputVars 매핑."""
    result = {
        "IGCC.DeNOX.AT_H1_901_PV": 25.0,
        "IGCC.CC.G1.DWATT": 250.0,
        "IGCC.CC.G1.TTXM": 580.0,
    }
    out = sim._result_to_outputvars(result)
    assert out.nox == 25.0
    assert out.power == 250.0
    assert out.exhaust_temp == 580.0


def test_result_to_outputvars_sets_lambda_efficiency_zero(sim):
    """lambda_, efficiency는 0.0 (engine/sim_loop 후처리)."""
    result = {
        "IGCC.DeNOX.AT_H1_901_PV": 25.0,
        "IGCC.CC.G1.DWATT": 250.0,
        "IGCC.CC.G1.TTXM": 580.0,
    }
    out = sim._result_to_outputvars(result)
    assert out.lambda_ == 0.0
    assert out.efficiency == 0.0
