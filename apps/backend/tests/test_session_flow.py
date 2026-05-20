"""세션 + 모드/리셋 + control 통합 테스트 (envelope v1)."""

import uuid

# 제어 변수 10개 태그 — DT_ARCHITECTURE.md §4 기준
CONTROL_TAGS = {
    "syngas": "IGCC.CC.G1.ca_fqsg_cl",
    "igv": "IGCC.CC.G1.csgv",
    "n2": "IGCC.CC.G1.NQKR3_MONITOR",
    "n2_valve_1": "IGCC.CC.G1.nicvs1",
    "syngas_srv": "IGCC.CC.G1.FSAGR",
    "syngas_gcv_1": "IGCC.CC.G1.FSAG11",
    "syngas_gcv_1a": "IGCC.CC.G1.FSAG11A",
    "syngas_gcv_2": "IGCC.CC.G1.FSAG12",
    "ibh_valve": "IGCC.CC.G1.CSBHX",
    "n2_flow": "IGCC.CC.G1.NQJ",
}


def _initial_payload():
    return {
        CONTROL_TAGS["syngas"]: 50.0,
        CONTROL_TAGS["igv"]: 75.0,
        CONTROL_TAGS["n2"]: 20.0,
        CONTROL_TAGS["n2_valve_1"]: 50.0,
        CONTROL_TAGS["syngas_srv"]: 60.0,
        CONTROL_TAGS["syngas_gcv_1"]: 55.0,
        CONTROL_TAGS["syngas_gcv_1a"]: 55.0,
        CONTROL_TAGS["syngas_gcv_2"]: 55.0,
        CONTROL_TAGS["ibh_valve"]: 30.0,
        CONTROL_TAGS["n2_flow"]: 30.0,
    }


def test_threshold_endpoint(client):
    res = client.get("/api/threshold")
    assert res.status_code == 200
    assert "nox_ppm_limit" in res.json()


def test_session_start_returns_envelope_metadata(client):
    res = client.post("/api/session/start", json={})
    assert res.status_code == 200
    body = res.json()
    assert body["sid"]
    assert body["mode"] == "sim"
    assert body["control_override"] is None
    assert "created_at" in body


def test_get_session_metadata(client):
    sid = client.post("/api/session/start", json={}).json()["sid"]
    res = client.get(f"/api/session/{sid}")
    assert res.status_code == 200
    body = res.json()
    assert body["sid"] == sid
    assert body["mode"] == "sim"
    assert body["control_override"] is None
    assert "created_at" in body and "last_active_at" in body


def test_get_session_snapshot_returns_last_stream_payload(client):
    sid = client.post("/api/session/start", json={}).json()["sid"]
    client.app.state.realtime_engine._last_payloads[sid] = {
        "v": 1,
        "sid": sid,
        "tick": 7,
        "ts": "2026-05-13T06:00:00.000Z",
        "mode": "realtime",
        "override_active": False,
        "current": {
            "controls": {
                "syngas_flow": 50.0,
                "igv_opening": 75.0,
                "n2_offset": 20.0,
                "n2_valve_1": 50.0,
                "syngas_srv": 60.0,
                "syngas_gcv_1": 55.0,
                "syngas_gcv_1a": 55.0,
                "syngas_gcv_2": 55.0,
                "ibh_valve": 30.0,
                "n2_flow": 30.0,
            },
            "outputs": {
                "nox": 28.5,
                "exhaust_temp": 580.0,
                "power": 165.2,
                "lambda_": 2.1,
                "efficiency": 0.42,
            },
        },
        "kafka_latest": None,
        "forecast": {
            "predicted_nox": 31.2,
            "target_time": "2026-05-13T06:05:00.000Z",
            "threshold_value": 30.0,
            "threshold_exceeded": True,
        },
        "warning": None,
    }

    res = client.get(f"/api/session/{sid}/snapshot")
    assert res.status_code == 200
    body = res.json()
    assert body["sid"] == sid
    assert body["t"] == 7
    assert body["current"]["syngas_flow"] == 50.0
    assert body["output"]["nox"] == 28.5
    assert body["output"]["predicted_nox"] == 31.2
    assert body["warning"] is False


def test_get_session_404(client):
    res = client.get("/api/session/non-existent")
    assert res.status_code == 404


def test_post_mode_realtime(client):
    sid = client.post("/api/session/start", json={}).json()["sid"]
    res = client.post(f"/api/session/{sid}/mode", json={"mode": "realtime"})
    assert res.status_code == 200
    assert res.json()["mode"] == "realtime"


def test_post_mode_invalid_400(client):
    sid = client.post("/api/session/start", json={}).json()["sid"]
    res = client.post(f"/api/session/{sid}/mode", json={"mode": "bogus"})
    # Pydantic literal validation은 422, 도메인 set_mode 검증은 400.
    # Pydantic이 먼저 걸러 422가 정상.
    assert res.status_code in (400, 422)


def test_post_control_then_override_set(client):
    sid = client.post("/api/session/start", json={}).json()["sid"]
    res = client.post(f"/api/session/{sid}/control", json=_initial_payload())
    assert res.status_code == 200
    assert res.json()["control_override_set"] is True

    info = client.get(f"/api/session/{sid}").json()
    assert info["control_override"] is not None


def test_post_control_in_realtime_409(client):
    sid = client.post("/api/session/start", json={}).json()["sid"]
    client.post(f"/api/session/{sid}/mode", json={"mode": "realtime"})
    res = client.post(f"/api/session/{sid}/control", json=_initial_payload())
    assert res.status_code == 409


def test_post_reset_clears_override(client):
    sid = client.post("/api/session/start", json={}).json()["sid"]
    client.post(f"/api/session/{sid}/control", json=_initial_payload())
    res = client.post(f"/api/session/{sid}/reset", json={})
    assert res.status_code == 200
    assert res.json()["control_override"] is None


def test_post_reset_realtime_is_noop(client):
    sid = client.post("/api/session/start", json={}).json()["sid"]
    client.post(f"/api/session/{sid}/mode", json={"mode": "realtime"})
    res = client.post(f"/api/session/{sid}/reset", json={})
    assert res.status_code == 200


def test_control_validation_range(client):
    sid = client.post("/api/session/start", json={}).json()["sid"]
    bad = {**_initial_payload(), CONTROL_TAGS["igv"]: 999.0}
    res = client.post(f"/api/session/{sid}/control", json=bad)
    # spec §2.1 — 값 범위 초과는 400 (Pydantic schema 오류와 구분)
    assert res.status_code == 400


def test_stop_unknown_sid_returns_ok(client):
    sid = str(uuid.uuid4())
    res = client.post(f"/api/session/{sid}/stop")
    assert res.status_code == 200


def test_stop_is_idempotent(client):
    sid = client.post("/api/session/start", json={}).json()["sid"]
    first = client.post(f"/api/session/{sid}/stop")
    second = client.post(f"/api/session/{sid}/stop")
    assert first.status_code == 200
    assert second.status_code == 200


def test_prediction_endpoint(client):
    res = client.post("/api/prediction", json={})
    assert res.status_code == 200
    body = res.json()
    for key in ("predicted_nox", "target_time", "threshold_exceeded", "threshold_value"):
        assert key in body


def test_prediction_endpoint_with_sid(client):
    sid = client.post("/api/session/start", json={}).json()["sid"]
    res = client.post("/api/prediction", json={"sid": sid})
    assert res.status_code == 200
    assert "predicted_nox" in res.json()
