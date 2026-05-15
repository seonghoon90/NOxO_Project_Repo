from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.realtime_engine import RealtimeEngine, correct_nox_15pct
from app.core.sensor_buffer import SensorBuffer
from app.core.session import Session
from app.core.session_context import SessionContext
from digital_twin.simulation import ControlVars, OutputVars


def _make_settings() -> MagicMock:
    """syngas_lhv 등 실제 후처리에 쓰이는 필드를 실수로 지정한 settings mock."""
    s = MagicMock()
    s.syngas_lhv = 11.0
    return s


def _make_context() -> SessionContext:
    """plant_context invariant 검증을 위해 실 SessionContext 사용 (MagicMock 회피)."""
    seed_buffer = SensorBuffer(maxlen=5)
    seed_buffer.load_bootstrap([
        {
            "syngas_flow": 100.0, "igv_opening": 80.0, "n2_offset": 5.0,
            "n2_valve_1": 42.0, "syngas_srv": 60.0, "syngas_gcv_1": 55.0,
            "syngas_gcv_1a": 54.0, "syngas_gcv_2": 53.0, "ibh_valve": 30.0,
            "n2_flow": 25.0, "exhaust_temp": 580.0,
        }
    ])
    return SessionContext.from_sensor_buffer("s1", seed_buffer)


def _make_buffer() -> SensorBuffer:
    buf = SensorBuffer(maxlen=10)
    buf.load_bootstrap([
        {
            "syngas_flow": 100.0, "igv_opening": 80.0, "n2_offset": 5.0,
            "n2_valve_1": 42.0, "syngas_srv": 60.0, "syngas_gcv_1": 55.0,
            "syngas_gcv_1a": 54.0, "syngas_gcv_2": 53.0, "ibh_valve": 30.0,
            "n2_flow": 25.0,
        }
    ])
    return buf


def _make_session(sid: str = "s1", mode: str = "sim") -> Session:
    now = datetime.now(timezone.utc)
    s = Session(sid=sid, context=_make_context(), created_at=now, last_active_at=now)
    if mode == "realtime":
        s.set_mode("realtime")
    return s


def _make_simulator() -> MagicMock:
    sim = MagicMock()
    sim.predict_for_session.return_value = OutputVars(
        nox=28.5, exhaust_temp=580.0, power=165.2, lambda_=2.1, efficiency=0.42,
    )
    return sim


def _make_forecaster(predicted: float = 31.2, name: str = "stub") -> MagicMock:
    # name은 _build_forecast_input의 분기 키 — 기본은 stub(features dict 경로)이고
    # ML 분기를 검증하는 케이스에서만 "ml"로 오버라이드한다.
    fc = MagicMock()
    fc.name = name
    fc.predict.return_value = predicted
    return fc


@pytest.mark.asyncio
async def test_sim_mode_no_override_emits_payload():
    buf = _make_buffer()
    session = _make_session(mode="sim")
    sessions = {"s1": session}
    sim = _make_simulator()
    fc = _make_forecaster()
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=sim, forecaster=fc,
        ws_manager=ws, sessions=sessions,
    )
    await engine._tick()

    assert sim.predict_for_session.called
    assert fc.predict.called is False  # sim 모드는 forecast 안 함
    ws.broadcast.assert_called_once()
    sid, payload = ws.broadcast.call_args[0]
    assert sid == "s1"
    assert payload["mode"] == "sim"
    assert payload["override_active"] is False
    assert payload["forecast"] is None
    assert payload["kafka_latest"] is None  # override=false면 null


@pytest.mark.asyncio
async def test_sim_mode_with_override_emits_kafka_latest():
    buf = _make_buffer()
    session = _make_session(mode="sim")
    session.set_override(ControlVars(
        syngas_flow=999.0, igv_opening=80.0, n2_offset=5.0, n2_valve_1=42.0,
        syngas_srv=60.0, syngas_gcv_1=55.0, syngas_gcv_1a=54.0, syngas_gcv_2=53.0,
        ibh_valve=30.0, n2_flow=25.0,
    ))
    sessions = {"s1": session}
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=_make_forecaster(), ws_manager=ws, sessions=sessions,
    )
    await engine._tick()

    payload = ws.broadcast.call_args[0][1]
    assert payload["override_active"] is True
    assert payload["current"]["controls"]["syngas_flow"] == 999.0
    assert payload["kafka_latest"] is not None
    assert payload["kafka_latest"]["controls"]["syngas_flow"] == 100.0


@pytest.mark.asyncio
async def test_realtime_mode_emits_forecast():
    buf = _make_buffer()
    session = _make_session(mode="realtime")
    sessions = {"s1": session}
    fc = _make_forecaster(predicted=31.2)
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=fc, ws_manager=ws, sessions=sessions,
    )
    await engine._tick()

    fc.predict.assert_called_once()
    payload = ws.broadcast.call_args[0][1]
    assert payload["mode"] == "realtime"
    assert payload["forecast"] is not None
    assert payload["forecast"]["predicted_nox"] == 31.2
    # buffer에 o2_pct가 없어 보정값은 raw 그대로 송신
    assert payload["forecast"]["predicted_nox_15pct"] == pytest.approx(31.2)


@pytest.mark.asyncio
async def test_forecaster_failure_yields_null_forecast():
    buf = _make_buffer()
    session = _make_session(mode="realtime")
    sessions = {"s1": session}
    fc = MagicMock()
    fc.name = "stub"
    fc.predict.side_effect = RuntimeError("model unavailable")
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=fc, ws_manager=ws, sessions=sessions,
    )
    await engine._tick()

    payload = ws.broadcast.call_args[0][1]
    assert payload["forecast"] is None
    assert payload["warning"] == "forecast unavailable"


@pytest.mark.asyncio
async def test_empty_buffer_sim_mode_still_broadcasts():
    """spec §2.3 — buffer 빈 상태에서도 sim 모드는 operating_point 폴백으로 broadcast."""
    buf = SensorBuffer(maxlen=10)  # 비어있음
    sessions = {"s1": _make_session(mode="sim")}
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=_make_forecaster(), ws_manager=ws, sessions=sessions,
    )
    await engine._tick()

    ws.broadcast.assert_called_once()
    payload = ws.broadcast.call_args[0][1]
    assert payload["mode"] == "sim"
    assert payload["warning"] is None  # sim 모드는 stale warning 미발신


@pytest.mark.asyncio
async def test_empty_buffer_realtime_mode_emits_stale_warning():
    """spec §2.3 — buffer 빈 상태에서 realtime 모드는 warning='kafka stream stale'."""
    buf = SensorBuffer(maxlen=10)
    sessions = {"s1": _make_session(mode="realtime")}
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=_make_forecaster(), ws_manager=ws, sessions=sessions,
    )
    await engine._tick()

    ws.broadcast.assert_called_once()
    payload = ws.broadcast.call_args[0][1]
    assert payload["mode"] == "realtime"
    assert payload["warning"] == "kafka stream stale"
    assert payload["forecast"] is None


@pytest.mark.asyncio
async def test_tick_increments_session_tick():
    buf = _make_buffer()
    session = _make_session()
    sessions = {"s1": session}

    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=_make_forecaster(), ws_manager=AsyncMock(),
        sessions=sessions,
    )
    assert session.tick == 0
    await engine._tick()
    assert session.tick == 1


# ML forecaster 분기 회귀 -------------------------------------------------
def _fill_buffer_warmed(session: Session, n: int = 460) -> None:
    """Plan E 차단을 통과시키는 helper — recent_df_buffer를 n행으로 채우고
    NOx에 변동을 부여해 _warmup_reason()=None 되게 한다.

    n=460은 _FORECAST_MIN_VALID_ROWS=450 + 약간 마진.
    """
    from digital_twin.forecaster.predict import DWATT_COL, TTXM_COL
    from digital_twin.forecaster.preprocess import NOX_TARGET_COL, RAW_FEATURES

    base = {col: 1.0 for col in RAW_FEATURES}
    base[TTXM_COL] = 580.0
    base[DWATT_COL] = 165.0
    for i in range(n):
        row = dict(base)
        row[NOX_TARGET_COL] = 28.0 + (i % 10) * 0.1  # 0~0.9 변동 → std≈0.3
        session.context.recent_df_buffer.append(row)


@pytest.mark.asyncio
async def test_realtime_ml_forecaster_receives_recent_df():
    """forecaster.name=='ml' 분기에서 ForecastInput.recent_df가 채워지고
    dt forecaster 필수 컬럼(RAW_FEATURES + TTXM + NOX + DWATT)이 0.0 폴백을 거쳐
    모두 포함되는지 검증. 옛 wiring(features만 채움)으로의 회귀 방지.
    """
    from app.adapters.forecaster import ForecastInput
    from digital_twin.forecaster.predict import DWATT_COL, TTXM_COL
    from digital_twin.forecaster.preprocess import NOX_TARGET_COL, RAW_FEATURES

    buf = _make_buffer()
    session = _make_session(mode="realtime")
    _fill_buffer_warmed(session)  # Plan E warmup 차단 통과
    sessions = {"s1": session}
    fc = _make_forecaster(predicted=42.5, name="ml")
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=fc, ws_manager=ws, sessions=sessions,
    )
    await engine._tick()

    fc.predict.assert_called_once()
    call_input = fc.predict.call_args[0][0]
    assert isinstance(call_input, ForecastInput)
    assert call_input.recent_df is not None, "ML 분기는 recent_df로 호출되어야 함"
    cols = set(call_input.recent_df.columns)
    required = set(RAW_FEATURES) | {TTXM_COL, NOX_TARGET_COL, DWATT_COL}
    missing = required - cols
    assert not missing, f"ML forecaster 필수 컬럼 누락: {sorted(missing)}"


# Plan E warmup 차단 -------------------------------------------------------
@pytest.mark.asyncio
async def test_ml_forecaster_skipped_when_buffer_too_short():
    """buf_len < 450이면 forecast 차단 + warning='forecast warmup'."""
    buf = _make_buffer()
    session = _make_session(mode="realtime")
    # 일부러 채우지 않음 — _make_context의 1행 시드만 존재 → buf_len=1
    fc = _make_forecaster(predicted=42.5, name="ml")
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=fc, ws_manager=ws, sessions={"s1": session},
    )
    await engine._tick()

    fc.predict.assert_not_called()
    payload = ws.broadcast.call_args[0][1]
    assert payload["warning"] == "forecast warmup"
    assert payload["forecast"] is None


@pytest.mark.asyncio
async def test_ml_forecaster_skipped_when_nox_stagnant():
    """NOx가 같은 값으로만 채워져 std<1e-3이면 차단."""
    from digital_twin.forecaster.preprocess import NOX_TARGET_COL, RAW_FEATURES
    from digital_twin.forecaster.predict import DWATT_COL, TTXM_COL

    buf = _make_buffer()
    session = _make_session(mode="realtime")
    # buf_len 통과 but NOx 단일값 → stagnation
    base = {col: 1.0 for col in RAW_FEATURES}
    base[TTXM_COL] = 580.0
    base[DWATT_COL] = 165.0
    base[NOX_TARGET_COL] = 28.0
    for _ in range(460):
        session.context.recent_df_buffer.append(dict(base))
    fc = _make_forecaster(predicted=42.5, name="ml")
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=fc, ws_manager=ws, sessions={"s1": session},
    )
    await engine._tick()

    fc.predict.assert_not_called()
    payload = ws.broadcast.call_args[0][1]
    assert payload["warning"] == "forecast warmup"


@pytest.mark.asyncio
async def test_stub_forecaster_not_blocked_by_warmup():
    """Stub Forecaster는 lag 미사용 → buf 짧아도 호출돼야 한다."""
    buf = _make_buffer()
    session = _make_session(mode="realtime")
    fc = _make_forecaster(predicted=31.2, name="stub")
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=fc, ws_manager=ws, sessions={"s1": session},
    )
    await engine._tick()

    fc.predict.assert_called_once()
    payload = ws.broadcast.call_args[0][1]
    assert payload["forecast"] is not None
    assert payload["warning"] is None


# Plan E 경계값 회귀 ------------------------------------------------------
@pytest.mark.asyncio
async def test_ml_forecaster_blocked_one_below_threshold():
    """tick 후 buf_len == 449 (임계-1)는 차단되어야 한다.
    `_step_session`이 매 tick recent_df_buffer.append(synthesized) 하므로 사전 447행 채우면 tick 후 449.
    `_warmup_reason`의 조건이 `<`가 아니라 더 느슨해지면(예: `<= 448`) 통과되어 실패."""
    from digital_twin.forecaster.preprocess import NOX_TARGET_COL, RAW_FEATURES
    from digital_twin.forecaster.predict import DWATT_COL, TTXM_COL

    buf = _make_buffer()
    session = _make_session(mode="realtime")
    base = {col: 1.0 for col in RAW_FEATURES}
    base[TTXM_COL] = 580.0
    base[DWATT_COL] = 165.0
    # 시드 1행 + 447행 추가 = 448. tick에서 synthesize 1행 추가 → 449 (= 임계-1).
    for i in range(447):
        row = dict(base)
        row[NOX_TARGET_COL] = 28.0 + (i % 10) * 0.1
        session.context.recent_df_buffer.append(row)
    assert len(session.context.recent_df_buffer) == 448

    fc = _make_forecaster(predicted=42.5, name="ml")
    ws = AsyncMock()
    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=fc, ws_manager=ws, sessions={"s1": session},
    )
    await engine._tick()

    assert len(session.context.recent_df_buffer) == 449
    fc.predict.assert_not_called()
    payload = ws.broadcast.call_args[0][1]
    assert payload["warning"] == "forecast warmup"


@pytest.mark.asyncio
async def test_ml_forecaster_filters_nan_and_bool_nox_values():
    """NOx 컬럼에 NaN·bool·문자열이 섞여도 _warmup_reason은 안전하게 필터링한다.
    필터 후 표본 수가 _FORECAST_MIN_NOX_SAMPLES 미만이면 nox_samples 사유로 차단."""
    from digital_twin.forecaster.preprocess import NOX_TARGET_COL, RAW_FEATURES
    from digital_twin.forecaster.predict import DWATT_COL, TTXM_COL

    buf = _make_buffer()
    session = _make_session(mode="realtime")
    base = {col: 1.0 for col in RAW_FEATURES}
    base[TTXM_COL] = 580.0
    base[DWATT_COL] = 165.0
    # buf_len 통과를 위해 460행 채우되 NOx는 모두 비숫자/NaN으로
    invalid_values = [float("nan"), float("inf"), True, False, "bad", None]
    for i in range(460):
        row = dict(base)
        row[NOX_TARGET_COL] = invalid_values[i % len(invalid_values)]
        session.context.recent_df_buffer.append(row)

    fc = _make_forecaster(predicted=42.5, name="ml")
    ws = AsyncMock()
    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=fc, ws_manager=ws, sessions={"s1": session},
    )
    await engine._tick()

    fc.predict.assert_not_called()
    payload = ws.broadcast.call_args[0][1]
    assert payload["warning"] == "forecast warmup"
    assert payload["forecast"] is None


@pytest.mark.asyncio
async def test_ml_forecaster_passes_when_nox_std_above_threshold():
    """nox_std > 1e-3 (충분한 변동)이면 차단 없이 predict 호출.
    _FORECAST_MIN_NOX_STD가 엄격 부등식(`<`)임을 회귀 보호."""
    from digital_twin.forecaster.preprocess import NOX_TARGET_COL, RAW_FEATURES
    from digital_twin.forecaster.predict import DWATT_COL, TTXM_COL

    buf = _make_buffer()
    session = _make_session(mode="realtime")
    base = {col: 1.0 for col in RAW_FEATURES}
    base[TTXM_COL] = 580.0
    base[DWATT_COL] = 165.0
    # 28.0과 28.01 교차 → std ≈ 0.005 > 1e-3 → 통과 예상
    for i in range(460):
        row = dict(base)
        row[NOX_TARGET_COL] = 28.0 + (i % 2) * 0.01
        session.context.recent_df_buffer.append(row)

    fc = _make_forecaster(predicted=42.5, name="ml")
    ws = AsyncMock()
    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=fc, ws_manager=ws, sessions={"s1": session},
    )
    await engine._tick()

    fc.predict.assert_called_once()
    payload = ws.broadcast.call_args[0][1]
    assert payload["warning"] is None
    assert payload["forecast"] is not None


# NOx 15% O2 보정식 ----------------------------------------------------------
def test_correct_nox_15pct_typical():
    # 표준 보정식: 30ppm @ 14% O2 → 30 * 5.9 / 6.9 ≈ 25.652
    assert correct_nox_15pct(30.0, 14.0) == pytest.approx(30.0 * 5.9 / 6.9)


def test_correct_nox_15pct_at_15pct_is_identity():
    # O2가 15%면 보정 계수 = 1 → 입력 그대로
    assert correct_nox_15pct(28.5, 15.0) == pytest.approx(28.5)


def test_correct_nox_15pct_returns_raw_when_o2_missing():
    assert correct_nox_15pct(28.5, None) == 28.5


def test_correct_nox_15pct_returns_raw_when_denom_near_zero():
    # 20.9 - 20.5 = 0.4 < MIN_DENOM(0.5) → 발산 방지로 raw 반환
    assert correct_nox_15pct(28.5, 20.5) == 28.5


def test_correct_nox_15pct_returns_raw_when_o2_negative():
    # 음수 O2(센서 fault) → raw 반환
    assert correct_nox_15pct(28.5, -1.0) == 28.5


@pytest.mark.asyncio
async def test_payload_outputs_includes_nox_15pct_from_kafka_o2():
    buf = SensorBuffer(maxlen=5)
    buf.load_bootstrap([
        {
            "syngas_flow": 100.0, "igv_opening": 80.0, "n2_offset": 5.0,
            "n2_valve_1": 42.0, "syngas_srv": 60.0, "syngas_gcv_1": 55.0,
            "syngas_gcv_1a": 54.0, "syngas_gcv_2": 53.0, "ibh_valve": 30.0,
            "n2_flow": 25.0, "o2_pct": 14.0,
        }
    ])
    session = _make_session(mode="sim")
    sessions = {"s1": session}
    ws = AsyncMock()
    engine = RealtimeEngine(
        settings=_make_settings(),
        sensor_buffer=buf, simulator=_make_simulator(),
        forecaster=_make_forecaster(), ws_manager=ws,
        sessions=sessions,
    )
    await engine._tick()

    payload = ws.broadcast.call_args[0][1]
    outputs = payload["current"]["outputs"]
    assert outputs["nox"] == pytest.approx(28.5)
    assert outputs["nox_15pct"] == pytest.approx(28.5 * 5.9 / 6.9)
