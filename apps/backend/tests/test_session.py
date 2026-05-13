from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock

from app.core.session import Session
from app.exceptions import SessionModeConflictError
from digital_twin.simulation import ControlVars


def _make_session(sid: str = "test-sid") -> Session:
    return Session(
        sid=sid,
        context=MagicMock(),
        created_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
    )


def _make_controls() -> ControlVars:
    return ControlVars(
        syngas_flow=100.0, igv_opening=80.0, n2_offset=5.0, n2_valve_1=42.0,
        syngas_srv=60.0, syngas_gcv_1=55.0, syngas_gcv_1a=54.0, syngas_gcv_2=53.0,
        ibh_valve=30.0, n2_flow=25.0,
    )


def test_default_mode_is_sim():
    s = _make_session()
    assert s.mode == "sim"
    assert s.control_override is None
    assert s.tick == 0


def test_set_mode_realtime_clears_override():
    s = _make_session()
    s.set_override(_make_controls())
    assert s.control_override is not None
    s.set_mode("realtime")
    assert s.mode == "realtime"
    assert s.control_override is None


def test_set_override_in_realtime_raises():
    s = _make_session()
    s.set_mode("realtime")
    with pytest.raises(SessionModeConflictError):
        s.set_override(_make_controls())


def test_clear_override_idempotent():
    s = _make_session()
    s.clear_override()
    s.clear_override()
    assert s.control_override is None


def test_clear_override_in_realtime_is_noop():
    s = _make_session()
    s.set_mode("realtime")
    s.clear_override()  # no error
    assert s.control_override is None


def test_set_mode_invalid_value_raises():
    s = _make_session()
    with pytest.raises(ValueError):
        s.set_mode("invalid")
