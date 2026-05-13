"""RealtimeEngine 통합 e2e — mock 없이 1 tick 실행.

리뷰 후속 회귀: BLOCKER 4(B1~B4) 재발 방지 — 실 SessionContext + StubSimulator로
buffer 키 네임스페이스 / lambda·efficiency 후처리 / Stub fallback 경로를 한 번에 검증.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.adapters.forecaster import StubForecaster
from app.adapters.simulator import StubSimulator
from app.config import Settings
from app.core.realtime_engine import RealtimeEngine
from app.core.sensor_buffer import SensorBuffer
from app.core.session import Session
from app.core.session_context import SessionContext


def _make_buffer() -> SensorBuffer:
    buf = SensorBuffer(maxlen=10)
    buf.load_bootstrap([
        {
            "syngas_flow": 1500.0, "igv_opening": 75.0, "n2_offset": 200.0,
            "n2_valve_1": 50.0, "syngas_srv": 60.0, "syngas_gcv_1": 55.0,
            "syngas_gcv_1a": 55.0, "syngas_gcv_2": 55.0, "ibh_valve": 30.0,
            "n2_flow": 100.0, "exhaust_temp": 580.0,
            # spec §2.2 — 이미 정규화된 UTC ISO 8601 + Z (lifespan/kafka_stream이 normalize 후 적재)
            "measured_at": "2025-08-25T00:00:00.000Z",
        }
    ])
    return buf


def _make_session(mode: str = "sim") -> Session:
    buf = _make_buffer()
    ctx = SessionContext.from_sensor_buffer("e2e-sid", buf)
    now = datetime.now(timezone.utc)
    session = Session(sid="e2e-sid", context=ctx, created_at=now, last_active_at=now)
    if mode == "realtime":
        session.set_mode("realtime")
    return session


@pytest.mark.asyncio
async def test_e2e_tick_sim_mode_broadcasts_full_envelope():
    """B1+B2+B3 통합 회귀 — 실 SessionContext + StubSimulator로 1 tick 후 envelope v1 완전체."""
    buf = _make_buffer()
    session = _make_session(mode="sim")
    sessions = {"e2e-sid": session}
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=Settings(),
        sensor_buffer=buf,
        simulator=StubSimulator(),
        forecaster=StubForecaster(),
        ws_manager=ws,
        sessions=sessions,
    )
    await engine._tick()

    ws.broadcast.assert_called_once()
    sid, payload = ws.broadcast.call_args[0]
    assert sid == "e2e-sid"
    # envelope v1 필드
    assert payload["v"] == 1
    assert payload["sid"] == "e2e-sid"
    assert payload["tick"] == 1
    assert payload["mode"] == "sim"
    assert payload["override_active"] is False
    assert payload["kafka_latest"] is None
    assert payload["forecast"] is None
    assert payload["warning"] is None
    # current.outputs — lambda_/efficiency가 후처리로 채워졌는지 (0.0이 아님)
    outputs = payload["current"]["outputs"]
    assert outputs["lambda_"] > 0.0
    assert 0.0 < outputs["efficiency"] <= 1.0
    assert outputs["nox"] > 0.0
    assert outputs["exhaust_temp"] > 0.0


@pytest.mark.asyncio
async def test_e2e_tick_realtime_mode_emits_forecast():
    """realtime 모드 — StubForecaster predict + envelope에 forecast 채움."""
    buf = _make_buffer()
    session = _make_session(mode="realtime")
    sessions = {"e2e-sid": session}
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=Settings(),
        sensor_buffer=buf,
        simulator=StubSimulator(),
        forecaster=StubForecaster(),
        ws_manager=ws,
        sessions=sessions,
    )
    await engine._tick()

    payload = ws.broadcast.call_args[0][1]
    assert payload["mode"] == "realtime"
    assert payload["forecast"] is not None
    assert "predicted_nox" in payload["forecast"]
    assert "target_time" in payload["forecast"]
    assert "threshold_value" in payload["forecast"]
    assert isinstance(payload["forecast"]["threshold_exceeded"], bool)


@pytest.mark.asyncio
async def test_e2e_tick_preserves_kafka_measured_at_with_override():
    """H3 회귀 — override active 시 kafka_latest.ts가 measured_at으로 보존."""
    from digital_twin.simulation import ControlVars

    buf = _make_buffer()
    session = _make_session(mode="sim")
    session.set_override(ControlVars(
        syngas_flow=1700.0, igv_opening=80.0, n2_offset=210.0, n2_valve_1=55.0,
        syngas_srv=62.0, syngas_gcv_1=56.0, syngas_gcv_1a=56.0, syngas_gcv_2=56.0,
        ibh_valve=32.0, n2_flow=110.0,
    ))
    sessions = {"e2e-sid": session}
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=Settings(),
        sensor_buffer=buf,
        simulator=StubSimulator(),
        forecaster=StubForecaster(),
        ws_manager=ws,
        sessions=sessions,
    )
    await engine._tick()

    payload = ws.broadcast.call_args[0][1]
    assert payload["override_active"] is True
    assert payload["kafka_latest"] is not None
    assert payload["kafka_latest"]["ts"] == "2025-08-25T00:00:00.000Z"
    # kafka_latest는 override 이전 원시값 — 1500.0 (override는 1700.0)
    assert payload["kafka_latest"]["controls"]["syngas_flow"] == 1500.0
    assert payload["current"]["controls"]["syngas_flow"] == 1700.0


@pytest.mark.asyncio
async def test_e2e_tick_caches_last_payload_for_ws_replay():
    """H2 회귀 — engine이 last_payload 캐시를 노출해 WS 재연결 시 즉시 push."""
    buf = _make_buffer()
    session = _make_session(mode="sim")
    sessions = {"e2e-sid": session}
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=Settings(),
        sensor_buffer=buf,
        simulator=StubSimulator(),
        forecaster=StubForecaster(),
        ws_manager=ws,
        sessions=sessions,
    )
    assert engine.last_payload("e2e-sid") is None
    await engine._tick()
    cached = engine.last_payload("e2e-sid")
    assert cached is not None
    assert cached["sid"] == "e2e-sid"
    assert cached["tick"] == 1

    engine.discard_session("e2e-sid")
    assert engine.last_payload("e2e-sid") is None


@pytest.mark.asyncio
async def test_e2e_synthesize_row_uses_raw_tag_namespace():
    """B2 회귀 — recent_df_buffer에 추가되는 row가 원천 태그 키로 통일."""
    buf = _make_buffer()
    session = _make_session(mode="sim")
    sessions = {"e2e-sid": session}
    ws = AsyncMock()
    initial_len = len(session.context.recent_df_buffer)

    engine = RealtimeEngine(
        settings=Settings(),
        sensor_buffer=buf,
        simulator=StubSimulator(),
        forecaster=StubForecaster(),
        ws_manager=ws,
        sessions=sessions,
    )
    await engine._tick()

    assert len(session.context.recent_df_buffer) == initial_len + 1
    last_row = session.context.recent_df_buffer[-1]
    # 원천 태그 키여야 함 (도메인 snake_case 키는 없어야 함)
    assert "IGCC.CC.G1.ca_fqsg_cl" in last_row
    assert "IGCC.CC.G1.csgv" in last_row
    assert "syngas_flow" not in last_row
    assert "igv_opening" not in last_row


@pytest.mark.asyncio
async def test_e2e_synthesize_row_preserves_plant_context_disturbance_columns():
    """2차 B1 회귀 — recent_df_buffer가 RAW 39 + TTXM 컬럼 보존 (외란 28개 포함).

    plant_context가 0.0 폴백한 외란 컬럼도 _synthesize_row가 베이스로 깔아 보존.
    deque(maxlen=900) evict 후에도 dt_predict의 recent_df 요구를 충족해야 함.
    """
    from digital_twin.preprocess import RAW_FEATURES

    buf = _make_buffer()
    session = _make_session(mode="sim")
    sessions = {"e2e-sid": session}
    ws = AsyncMock()

    engine = RealtimeEngine(
        settings=Settings(),
        sensor_buffer=buf,
        simulator=StubSimulator(),
        forecaster=StubForecaster(),
        ws_manager=ws,
        sessions=sessions,
    )
    await engine._tick()

    last_row = session.context.recent_df_buffer[-1]
    # RAW_FEATURES 39개 + TTXM 1개 = 40개 컬럼이 모두 존재
    for col in RAW_FEATURES:
        assert col in last_row, f"missing column in synthesized row: {col}"
    assert "IGCC.CC.G1.TTXM" in last_row


@pytest.mark.asyncio
async def test_e2e_submit_control_sets_pending_input_flag():
    """2차 H1 회귀 — Session.set_override가 pending_input_flag + last_input_t set.

    spec §2.1 — 사용자 제어 입력 후 debounce 1초 경과 시 ML 즉시 호출 가능.
    """
    from digital_twin.simulation import ControlVars

    session = _make_session(mode="sim")
    assert session.context.pending_input_flag is False
    assert session.context.last_input_t == 0.0

    session.set_override(ControlVars(
        syngas_flow=1700.0, igv_opening=80.0, n2_offset=210.0, n2_valve_1=55.0,
        syngas_srv=62.0, syngas_gcv_1=56.0, syngas_gcv_1a=56.0, syngas_gcv_2=56.0,
        ibh_valve=32.0, n2_flow=110.0,
    ))

    assert session.context.pending_input_flag is True
    assert session.context.last_input_t > 0.0


@pytest.mark.asyncio
async def test_e2e_realtime_stale_skips_buffer_append():
    """2차 H4 회귀 — realtime + stale: fallback row가 buffer에 누적되지 않음."""
    buf = SensorBuffer(maxlen=10)  # 비어있음 → stale
    session = _make_session(mode="realtime")
    sessions = {"e2e-sid": session}
    ws = AsyncMock()
    initial_len = len(session.context.recent_df_buffer)

    engine = RealtimeEngine(
        settings=Settings(),
        sensor_buffer=buf,
        simulator=StubSimulator(),
        forecaster=StubForecaster(),
        ws_manager=ws,
        sessions=sessions,
    )
    await engine._tick()
    await engine._tick()
    await engine._tick()

    # realtime + stream stale 3 tick → buffer는 변화 없음
    assert len(session.context.recent_df_buffer) == initial_len
    # 그래도 broadcast는 stale warning과 함께 발생
    assert ws.broadcast.call_count == 3
    payload = ws.broadcast.call_args[0][1]
    assert payload["warning"] == "kafka stream stale"


@pytest.mark.asyncio
async def test_e2e_sim_stale_continues_buffer_append():
    """2차 H4 회귀 — sim 모드는 stale에도 fallback row를 buffer에 push (자기재생)."""
    buf = SensorBuffer(maxlen=10)  # 비어있음 → stale
    session = _make_session(mode="sim")
    sessions = {"e2e-sid": session}
    ws = AsyncMock()
    initial_len = len(session.context.recent_df_buffer)

    engine = RealtimeEngine(
        settings=Settings(),
        sensor_buffer=buf,
        simulator=StubSimulator(),
        forecaster=StubForecaster(),
        ws_manager=ws,
        sessions=sessions,
    )
    await engine._tick()
    await engine._tick()

    assert len(session.context.recent_df_buffer) == initial_len + 2
