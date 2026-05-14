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


def _make_forecaster(predicted: float = 31.2) -> MagicMock:
    fc = MagicMock()
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
