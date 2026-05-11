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


@pytest.fixture
def ctx_with_cached(make_ctx):
    """게이트 close 케이스용 — cached_output_target 미리 채움 (P6)."""
    out = OutputVars(nox=20.0, exhaust_temp=580.0, power=248.6,
                     lambda_=1.1, efficiency=0.89)
    return make_ctx(cached_output_target=out, last_ml_call_t=0.0)


def test_predict_returns_cached_when_gate_closed(sim, ctx_with_cached, monkeypatch):
    """게이트 close (60초 미경과, input 없음) → cached 반환."""
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: 30.0)
    from digital_twin.simulation import ControlVars
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    out = sim.predict_for_session(controls, ctx_with_cached)
    assert out.nox == 20.0


def test_predict_raises_when_cache_invariant_violated(sim, make_ctx, monkeypatch):
    """cached_output_target=None인데 게이트 close → SessionTerminatedError (P4)."""
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: 30.0)
    ctx = make_ctx(last_ml_call_t=0.0, cached_output_target=None)
    from digital_twin.simulation import ControlVars
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    with pytest.raises(SessionTerminatedError, match="cache_invariant_violation"):
        sim.predict_for_session(controls, ctx)


def test_predict_calls_dt_predict_after_interval(sim, ctx_with_cached, monkeypatch):
    """60초 경과 → dt_predict 호출, cached 갱신."""
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: 60.1)
    # plant_context를 RAW 외란 + TTXM으로 채워야 _build_current_row 동작
    from digital_twin.preprocess import RAW_FEATURES
    disturbance = [c for c in RAW_FEATURES if c not in __import__("app.domain.tags", fromlist=["CONTROL_TAGS"]).CONTROL_TAGS]
    ctx_with_cached.plant_context = {k: 1.0 for k in disturbance}
    ctx_with_cached.plant_context["IGCC.CC.G1.TTXM"] = 580.0
    # buffer에 60행 이상
    from app.domain.tags import CONTROL_TAGS
    for _ in range(100):
        ctx_with_cached.push_step_row({tag: 1.0 for tag in CONTROL_TAGS})
    fake_result = {
        "IGCC.DeNOX.AT_H1_901_PV": 30.0,
        "IGCC.CC.G1.DWATT": 260.0,
        "IGCC.CC.G1.TTXM": 590.0,
    }
    monkeypatch.setattr(
        "app.adapters.simulator.ml.dt_predict",
        lambda model, inputs, recent_df: fake_result,
    )
    from digital_twin.simulation import ControlVars
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    out = sim.predict_for_session(controls, ctx_with_cached)
    assert out.nox == 30.0
    assert ctx_with_cached.cached_output_target.nox == 30.0


def test_predict_updates_last_ml_call_t_on_success(sim, ctx_with_cached, monkeypatch):
    """성공 호출 후 last_ml_call_t = now."""
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: 60.1)
    from digital_twin.preprocess import RAW_FEATURES
    disturbance = [c for c in RAW_FEATURES if c not in __import__("app.domain.tags", fromlist=["CONTROL_TAGS"]).CONTROL_TAGS]
    ctx_with_cached.plant_context = {k: 1.0 for k in disturbance}
    ctx_with_cached.plant_context["IGCC.CC.G1.TTXM"] = 580.0
    monkeypatch.setattr(
        "app.adapters.simulator.ml.dt_predict",
        lambda model, inputs, recent_df: {
            "IGCC.DeNOX.AT_H1_901_PV": 30.0, "IGCC.CC.G1.DWATT": 260.0, "IGCC.CC.G1.TTXM": 590.0,
        },
    )
    from digital_twin.simulation import ControlVars
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    sim.predict_for_session(controls, ctx_with_cached)
    assert ctx_with_cached.last_ml_call_t == 60.1


def test_predict_resets_pending_flag_only_on_input_gate(sim, ctx_with_cached, monkeypatch):
    """C4 — interval 게이트로 호출됐을 때 pending 유지."""
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: 60.1)
    ctx_with_cached.pending_input_flag = True
    ctx_with_cached.last_input_t = 60.0  # debounce 0.1s 미충족
    from digital_twin.preprocess import RAW_FEATURES
    disturbance = [c for c in RAW_FEATURES if c not in __import__("app.domain.tags", fromlist=["CONTROL_TAGS"]).CONTROL_TAGS]
    ctx_with_cached.plant_context = {k: 1.0 for k in disturbance}
    ctx_with_cached.plant_context["IGCC.CC.G1.TTXM"] = 580.0
    monkeypatch.setattr(
        "app.adapters.simulator.ml.dt_predict",
        lambda model, inputs, recent_df: {
            "IGCC.DeNOX.AT_H1_901_PV": 30.0, "IGCC.CC.G1.DWATT": 260.0, "IGCC.CC.G1.TTXM": 590.0,
        },
    )
    from digital_twin.simulation import ControlVars
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    sim.predict_for_session(controls, ctx_with_cached)
    assert ctx_with_cached.pending_input_flag is True  # interval gate라 유지


def test_predict_increments_failure_count_on_exception(sim, ctx_with_cached, monkeypatch):
    """dt_predict raise → ml_failure_count += 1."""
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: 60.1)
    from digital_twin.preprocess import RAW_FEATURES
    disturbance = [c for c in RAW_FEATURES if c not in __import__("app.domain.tags", fromlist=["CONTROL_TAGS"]).CONTROL_TAGS]
    ctx_with_cached.plant_context = {k: 1.0 for k in disturbance}
    ctx_with_cached.plant_context["IGCC.CC.G1.TTXM"] = 580.0

    def boom(**kwargs):
        raise RuntimeError("transient")
    monkeypatch.setattr("app.adapters.simulator.ml.dt_predict", boom)
    from digital_twin.simulation import ControlVars
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    sim.predict_for_session(controls, ctx_with_cached)
    assert ctx_with_cached.ml_failure_count == 1


def test_predict_returns_cached_on_single_failure(sim, ctx_with_cached, monkeypatch):
    """1~4회 실패는 cached 반환."""
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: 60.1)
    from digital_twin.preprocess import RAW_FEATURES
    disturbance = [c for c in RAW_FEATURES if c not in __import__("app.domain.tags", fromlist=["CONTROL_TAGS"]).CONTROL_TAGS]
    ctx_with_cached.plant_context = {k: 1.0 for k in disturbance}
    ctx_with_cached.plant_context["IGCC.CC.G1.TTXM"] = 580.0
    monkeypatch.setattr("app.adapters.simulator.ml.dt_predict",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("x")))
    from digital_twin.simulation import ControlVars
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    out = sim.predict_for_session(controls, ctx_with_cached)
    assert out.nox == 20.0  # cached value


def test_predict_raises_session_terminated_after_5_failures(sim, ctx_with_cached, monkeypatch):
    """5회 연속 실패 → SessionTerminatedError."""
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: 60.1)
    from digital_twin.preprocess import RAW_FEATURES
    disturbance = [c for c in RAW_FEATURES if c not in __import__("app.domain.tags", fromlist=["CONTROL_TAGS"]).CONTROL_TAGS]
    ctx_with_cached.plant_context = {k: 1.0 for k in disturbance}
    ctx_with_cached.plant_context["IGCC.CC.G1.TTXM"] = 580.0
    ctx_with_cached.ml_failure_count = 4
    monkeypatch.setattr("app.adapters.simulator.ml.dt_predict",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("x")))
    from digital_twin.simulation import ControlVars
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    with pytest.raises(SessionTerminatedError):
        sim.predict_for_session(controls, ctx_with_cached)


def test_predict_resets_failure_count_on_success(sim, ctx_with_cached, monkeypatch):
    """성공 호출 후 ml_failure_count = 0."""
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: 60.1)
    from digital_twin.preprocess import RAW_FEATURES
    disturbance = [c for c in RAW_FEATURES if c not in __import__("app.domain.tags", fromlist=["CONTROL_TAGS"]).CONTROL_TAGS]
    ctx_with_cached.plant_context = {k: 1.0 for k in disturbance}
    ctx_with_cached.plant_context["IGCC.CC.G1.TTXM"] = 580.0
    ctx_with_cached.ml_failure_count = 3
    monkeypatch.setattr(
        "app.adapters.simulator.ml.dt_predict",
        lambda **kw: {"IGCC.DeNOX.AT_H1_901_PV": 30.0, "IGCC.CC.G1.DWATT": 260.0, "IGCC.CC.G1.TTXM": 590.0},
    )
    from digital_twin.simulation import ControlVars
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    sim.predict_for_session(controls, ctx_with_cached)
    assert ctx_with_cached.ml_failure_count == 0


def test_failure_count_reset_then_can_accumulate_again(sim, ctx_with_cached, monkeypatch):
    """4회 실패 → 1회 성공(0 리셋) → 다시 5회 누적 가능."""
    fake_times = iter([60.1, 120.2, 120.2, 120.2])
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: next(fake_times))
    from digital_twin.preprocess import RAW_FEATURES
    disturbance = [c for c in RAW_FEATURES if c not in __import__("app.domain.tags", fromlist=["CONTROL_TAGS"]).CONTROL_TAGS]
    ctx_with_cached.plant_context = {k: 1.0 for k in disturbance}
    ctx_with_cached.plant_context["IGCC.CC.G1.TTXM"] = 580.0
    ctx_with_cached.ml_failure_count = 4
    # 1번째: 성공
    monkeypatch.setattr(
        "app.adapters.simulator.ml.dt_predict",
        lambda **kw: {"IGCC.DeNOX.AT_H1_901_PV": 30.0, "IGCC.CC.G1.DWATT": 260.0, "IGCC.CC.G1.TTXM": 590.0},
    )
    from digital_twin.simulation import ControlVars
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    sim.predict_for_session(controls, ctx_with_cached)
    assert ctx_with_cached.ml_failure_count == 0
    # 이후 실패 → 1회로 누적 (5에서 raise 아님)
    monkeypatch.setattr("app.adapters.simulator.ml.dt_predict",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("x")))
    sim.predict_for_session(controls, ctx_with_cached)
    assert ctx_with_cached.ml_failure_count == 1
