"""SessionService 단일화 후 기능 테스트."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.core.sensor_buffer import SensorBuffer
from app.exceptions import SessionModeConflictError
from app.services.session_service import SessionService
from digital_twin.simulation import ControlVars


def _make_controls() -> ControlVars:
    return ControlVars(
        syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0, n2_valve_1=50.0,
        syngas_srv=60.0, syngas_gcv_1=55.0, syngas_gcv_1a=55.0, syngas_gcv_2=55.0,
        ibh_valve=30.0, n2_flow=100.0,
    )


def _make_buffer() -> SensorBuffer:
    buf = SensorBuffer(maxlen=900)
    buf.load_bootstrap([
        {
            "syngas_flow": 1500.0, "igv_opening": 75.0,
            "n2_offset": 200.0, "n2_valve_1": 50.0,
            "syngas_srv": 60.0, "syngas_gcv_1": 55.0,
            "syngas_gcv_1a": 55.0, "syngas_gcv_2": 55.0,
            "ibh_valve": 30.0, "n2_flow": 100.0,
        }
    ])
    return buf


@pytest.fixture
def service():
    return SessionService(
        settings=Settings(),
        sessions={},
        sensor_buffer=_make_buffer(),
        ws_manager=AsyncMock(),
        simulation_log_repo=None,
    )


def test_start_creates_sim_mode_session(service):
    session = service.start()
    assert session.mode == "sim"
    assert session.control_override is None


def test_set_mode_realtime(service):
    session = service.start()
    service.set_mode(session.sid, "realtime")
    assert session.mode == "realtime"


def test_set_mode_invalid_raises_value_error(service):
    session = service.start()
    with pytest.raises(ValueError):
        service.set_mode(session.sid, "bogus")


def test_submit_control_sets_override(service):
    session = service.start()
    service.submit_control(session.sid, _make_controls())
    assert session.control_override is not None


def test_submit_control_in_realtime_raises(service):
    session = service.start()
    service.set_mode(session.sid, "realtime")
    with pytest.raises(SessionModeConflictError):
        service.submit_control(session.sid, _make_controls())


def test_reset_override_idempotent_in_realtime(service):
    session = service.start()
    service.set_mode(session.sid, "realtime")
    service.reset_override(session.sid)  # no error
    assert session.control_override is None


def test_stop_missing_sid_still_runs_best_effort_cleanup():
    service = SessionService(
        settings=Settings(),
        sessions={},
        sensor_buffer=_make_buffer(),
        ws_manager=AsyncMock(),
        simulation_log_repo=None,
    )
    asyncio.run(service.stop("orphan-sid"))
    service.ws_manager.drop_session.assert_called_once_with("orphan-sid")
