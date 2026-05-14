from datetime import datetime, timezone
import pytest

from app.schemas.stream import (
    RealtimeStreamPayload,
    StreamControls,
    StreamOutputs,
    StreamCurrent,
    StreamKafkaLatest,
    StreamForecast,
)


def _make_controls() -> StreamControls:
    return StreamControls(
        syngas_flow=100.0, igv_opening=80.0, n2_offset=5.0, n2_valve_1=42.0,
        syngas_srv=60.0, syngas_gcv_1=55.0, syngas_gcv_1a=54.0, syngas_gcv_2=53.0,
        ibh_valve=30.0, n2_flow=25.0,
    )


def _make_outputs() -> StreamOutputs:
    return StreamOutputs(
        nox=28.5, nox_15pct=24.36, exhaust_temp=580.0, power=165.2,
        lambda_=2.1, efficiency=0.42,
    )


def test_sim_no_override_payload():
    payload = RealtimeStreamPayload(
        v=1, sid="abc", tick=1,
        ts=datetime.now(timezone.utc),
        mode="sim",
        override_active=False,
        current=StreamCurrent(controls=_make_controls(), outputs=_make_outputs()),
        kafka_latest=None,
        forecast=None,
        warning=None,
    )
    dumped = payload.model_dump(by_alias=True, mode="json")
    assert dumped["v"] == 1
    assert dumped["mode"] == "sim"
    assert dumped["override_active"] is False
    assert dumped["forecast"] is None
    assert dumped["current"]["outputs"]["lambda_"] == 2.1


def test_realtime_with_forecast():
    payload = RealtimeStreamPayload(
        v=1, sid="abc", tick=10,
        ts=datetime.now(timezone.utc),
        mode="realtime",
        override_active=False,
        current=StreamCurrent(controls=_make_controls(), outputs=_make_outputs()),
        kafka_latest=None,
        forecast=StreamForecast(
            predicted_nox=31.2,
            predicted_nox_15pct=26.68,
            target_time=datetime.now(timezone.utc),
            threshold_value=30.0,
            threshold_exceeded=True,
        ),
        warning=None,
    )
    dumped = payload.model_dump(by_alias=True, mode="json")
    assert dumped["forecast"]["predicted_nox"] == 31.2
    assert dumped["forecast"]["threshold_exceeded"] is True


def test_sim_with_override_includes_kafka_latest():
    payload = RealtimeStreamPayload(
        v=1, sid="abc", tick=20,
        ts=datetime.now(timezone.utc),
        mode="sim",
        override_active=True,
        current=StreamCurrent(controls=_make_controls(), outputs=_make_outputs()),
        kafka_latest=StreamKafkaLatest(
            controls=_make_controls(),
            ts=datetime.now(timezone.utc),
        ),
        forecast=None,
        warning=None,
    )
    dumped = payload.model_dump(by_alias=True, mode="json")
    assert dumped["override_active"] is True
    assert dumped["kafka_latest"] is not None


def test_invalid_mode_rejected():
    with pytest.raises(Exception):
        RealtimeStreamPayload(
            v=1, sid="abc", tick=1,
            ts=datetime.now(timezone.utc),
            mode="bogus",  # type: ignore
            override_active=False,
            current=StreamCurrent(controls=_make_controls(), outputs=_make_outputs()),
            kafka_latest=None, forecast=None, warning=None,
        )
