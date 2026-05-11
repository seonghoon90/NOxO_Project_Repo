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
