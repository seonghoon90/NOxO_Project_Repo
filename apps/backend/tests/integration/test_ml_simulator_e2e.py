from collections import deque
from unittest.mock import AsyncMock, MagicMock
import pandas as pd
import pytest

from app.adapters.simulator.ml import MLSimulator
from app.core.session_context import SessionContext
from app.domain.tags import CONTROL_TAGS
from digital_twin.preprocess import RAW_FEATURES
from digital_twin.simulation import ControlVars


def _fake_snapshot_df(rows: int = 900) -> pd.DataFrame:
    cols = ["measured_at"] + list(RAW_FEATURES) + ["IGCC.DeNOX.AT_H1_901_PV", "IGCC.CC.G1.DWATT", "IGCC.CC.G1.TTXM"]
    return pd.DataFrame({c: [1.0] * rows if c != "measured_at"
                         else pd.date_range("2026-05-11", periods=rows, freq="1s")
                         for c in cols})


@pytest.fixture
def ml_simulator_with_dummy_models(patched_models_dir):
    return MLSimulator(models_dir=patched_models_dir)


@pytest.mark.integration
def test_e2e_predict_for_session_with_real_dummy_model(ml_simulator_with_dummy_models, monkeypatch):
    """더미 모델로 예측 성공 + cached_output_target 채워짐."""
    sim = ml_simulator_with_dummy_models
    df = _fake_snapshot_df(900)
    ctx = SessionContext.from_snapshot("sid-e2e", df)
    # 운영 패턴 시뮬: time.monotonic()이 boot 후 누적 시간이라 항상 last_ml_call_t(=0.0)보다 크다.
    # 100.0 - 0.0 >= 60.0 → interval gate trip → 첫 호출 ML 발화.
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: 100.0)
    controls = ControlVars(
        syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
        n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
        syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0,
    )
    # 초기 호출 — interval gate 트립
    out = sim.predict_for_session(controls, ctx)
    assert out.nox is not None
    assert ctx.cached_output_target is not None


@pytest.mark.integration
def test_e2e_freeze_policy_preserves_disturbance_values(ml_simulator_with_dummy_models):
    """매 push 후에도 buffer 외란 컬럼은 스냅샷 freeze 값 유지 (NS-freeze invariant).

    스냅샷의 disturbance 값을 식별 가능한 sentinel(42.0)로, control은 1.0으로 설정한 뒤
    push_step_row가 다른 control 값(999.0)을 넣어도 disturbance가 42.0 그대로인지 검증.
    """
    # 외란 sentinel 42.0, 제어 1.0 — push 시 의도적으로 999.0을 넣어 freeze 깨짐 여부 검출
    rows = 900
    base_cols = ["measured_at"] + list(RAW_FEATURES) + ["IGCC.DeNOX.AT_H1_901_PV", "IGCC.CC.G1.DWATT", "IGCC.CC.G1.TTXM"]
    data = {}
    for c in base_cols:
        if c == "measured_at":
            data[c] = pd.date_range("2026-05-11", periods=rows, freq="1s")
        elif c in CONTROL_TAGS:
            data[c] = [1.0] * rows
        else:
            data[c] = [42.0] * rows  # 외란 + TTXM + target 모두 sentinel
    df = pd.DataFrame(data)

    ctx = SessionContext.from_snapshot("sid-e2e2", df)
    # 외란 키 (RAW - CONTROL_TAGS) 하나 선택해 freeze 값 확인
    dist_key = next(c for c in RAW_FEATURES if c not in CONTROL_TAGS)
    assert ctx.plant_context[dist_key] == 42.0  # snapshot으로부터 freeze

    # 의도적으로 다른 제어 값(999.0)으로 5번 push
    for _ in range(5):
        ctx.push_step_row({tag: 999.0 for tag in CONTROL_TAGS})

    # 외란은 freeze된 42.0, 제어만 999.0 — push_step_row의 dict merge 순서 검증
    last_row = ctx.recent_df_buffer[-1]
    for k in RAW_FEATURES:
        if k not in CONTROL_TAGS:
            assert last_row[k] == 42.0, f"{k} freeze 깨짐: expected 42.0, got {last_row[k]}"
        else:
            assert last_row[k] == 999.0, f"{k} 제어값 미반영: expected 999.0, got {last_row[k]}"


@pytest.mark.integration
def test_e2e_initial_ml_call_populates_cached_output(ml_simulator_with_dummy_models, monkeypatch):
    """NS12 — predict_for_session 1회 호출이 cached_output_target을 채운다."""
    sim = ml_simulator_with_dummy_models
    df = _fake_snapshot_df(900)
    ctx = SessionContext.from_snapshot("sid-e2e3", df)
    # 운영 패턴 시뮬: time.monotonic()이 boot 후 누적 시간이라 항상 last_ml_call_t(=0.0)보다 크다.
    # 100.0 - 0.0 >= 60.0 → interval gate trip → 첫 호출 ML 발화.
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: 100.0)
    assert ctx.cached_output_target is None
    controls = ControlVars(
        syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
        n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
        syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0,
    )
    sim.predict_for_session(controls, ctx)
    assert ctx.cached_output_target is not None


# === Task 14 통합 그룹 (W1~W4) — trigger / fallback / terminate / long-freeze ===

@pytest.mark.integration
def test_e2e_ml_trigger_on_user_input(ml_simulator_with_dummy_models, monkeypatch):
    """사용자 입력 후 1초 debounce 지나면 ML 호출되어 cached 갱신.

    Deviation from plan: time.monotonic은 production에서 boot uptime(큰 값)이라
    `last_ml_call_t=0.0` 대비 초기 호출이 자동 trip. test 환경도 같은 패턴 시뮬을 위해
    fake_t[0]=100.0으로 시작 (Task 12 monkeypatch 게이트 버그 동일 패턴)."""
    sim = ml_simulator_with_dummy_models
    df = _fake_snapshot_df(900)
    ctx = SessionContext.from_snapshot("sid-trigger", df)
    fake_t = [100.0]
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: fake_t[0])
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    # 초기 호출 — interval gate (100.0 - 0.0 >= 60)
    sim.predict_for_session(controls, ctx)
    first_call_t = ctx.last_ml_call_t
    # 입력 발생
    ctx.pending_input_flag = True
    ctx.last_input_t = fake_t[0]
    fake_t[0] += 1.5  # debounce 충족
    sim.predict_for_session(controls, ctx)
    assert ctx.last_ml_call_t > first_call_t


@pytest.mark.integration
def test_e2e_ml_fallback_interval(ml_simulator_with_dummy_models, monkeypatch):
    """60초 동안 입력 없으면 정기 ML 호출.

    Deviation from plan: fake_t[0]=100.0 시작 (Task 12 게이트 버그 패턴)."""
    sim = ml_simulator_with_dummy_models
    df = _fake_snapshot_df(900)
    ctx = SessionContext.from_snapshot("sid-fallback", df)
    fake_t = [100.0]
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: fake_t[0])
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    sim.predict_for_session(controls, ctx)
    first_t = ctx.last_ml_call_t
    fake_t[0] = first_t + 60.1
    sim.predict_for_session(controls, ctx)
    assert ctx.last_ml_call_t > first_t + 60.0


@pytest.mark.integration
def test_e2e_session_terminates_on_repeated_ml_failures(ml_simulator_with_dummy_models, monkeypatch):
    """ML이 5회 연속 실패하면 SessionTerminatedError.

    Deviation from plan: monkeypatch를 초기 호출 이전에 걸어야 last_ml_call_t를
    fake_t에 동기화 가능. plan은 초기 호출 후 monkeypatch라 실제 monotonic 값이
    cached 시점에 박혀 이후 fake_t와 mismatch."""
    from app.exceptions import SessionTerminatedError
    sim = ml_simulator_with_dummy_models
    df = _fake_snapshot_df(900)
    ctx = SessionContext.from_snapshot("sid-fail", df)
    # fake_t 먼저 걸어 초기 호출의 last_ml_call_t를 통제 가능하게 함
    fake_t = [100.0]
    monkeypatch.setattr("app.adapters.simulator.ml.time.monotonic", lambda: fake_t[0])
    controls = ControlVars(syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0,
                           n2_valve_1=50.0, syngas_srv=60.0, syngas_gcv_1=55.0,
                           syngas_gcv_1a=55.0, syngas_gcv_2=55.0, ibh_valve=30.0, n2_flow=100.0)
    # cached 미리 채움 (성공 — last_ml_call_t=100.0)
    sim.predict_for_session(controls, ctx)
    # dt_predict 강제 실패
    monkeypatch.setattr("app.adapters.simulator.ml.dt_predict",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    # 4번 실패 (count 1,2,3,4) — cached 반환
    for _ in range(4):
        fake_t[0] += 60.1
        sim.predict_for_session(controls, ctx)
    # 5번째 실패 → count=5 → raise
    fake_t[0] += 60.1
    with pytest.raises(SessionTerminatedError):
        sim.predict_for_session(controls, ctx)


@pytest.mark.integration
def test_e2e_freeze_policy_after_multiple_pushes(ml_simulator_with_dummy_models):
    """매 push 후에도 buffer 외란 컬럼은 스냅샷 값 유지 (장기 freeze 검증)."""
    sim = ml_simulator_with_dummy_models
    df = _fake_snapshot_df(900)
    ctx = SessionContext.from_snapshot("sid-freeze-long", df)
    disturbance_keys = [c for c in RAW_FEATURES if c not in CONTROL_TAGS]
    initial_disturbance_snapshot = {k: ctx.plant_context[k] for k in disturbance_keys}
    # 200번 push (장기 시뮬)
    for i in range(200):
        ctx.push_step_row({tag: float(i) for tag in CONTROL_TAGS})
    last_row = ctx.recent_df_buffer[-1]
    for k, v in initial_disturbance_snapshot.items():
        assert last_row[k] == v
