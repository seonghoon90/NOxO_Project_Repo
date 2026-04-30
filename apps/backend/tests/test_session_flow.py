"""세션 + control + WebSocket 통합 테스트.

프론트엔드가 실제로 따라가는 시나리오를 그대로 재현:
  start → control 변경 → WS로 push 받은 메시지에서 변화 확인 → stop.
"""

import json
import uuid

CONTROL_TAGS = {
    "syngas": "IGCC.CC.G1.ca_fqsg_cl",
    "n2": "IGCC.CC.G1.NQKR3_MONITOR",
    "igv": "IGCC.CC.G1.csgv",
}


def _initial_payload():
    return {
        CONTROL_TAGS["syngas"]: 1500.0,
        CONTROL_TAGS["n2"]: 200.0,
        CONTROL_TAGS["igv"]: 75.0,
    }


def test_threshold_endpoint(client):
    res = client.get("/api/threshold")
    assert res.status_code == 200
    assert "nox_ppm_limit" in res.json()


def test_session_lifecycle(client):
    # 1. 세션 시작
    res = client.post("/api/session/start", json={"initial_condition": _initial_payload()})
    assert res.status_code == 200
    body = res.json()
    sid = body["sid"]
    assert sid

    # 2. snapshot 조회
    res = client.get(f"/api/session/{sid}/snapshot")
    assert res.status_code == 200
    snap = res.json()
    assert snap["sid"] == sid
    assert snap["target"][CONTROL_TAGS["syngas"]] == 1500.0
    assert "nox" in snap["output"]
    assert "lambda" in snap["output"]
    assert "power" in snap["output"]

    # 3. control 변경 (합성가스 유량 ↑)
    new_payload = {**_initial_payload(), CONTROL_TAGS["syngas"]: 1800.0}
    res = client.post(f"/api/session/{sid}/control", json=new_payload)
    assert res.status_code == 200
    assert res.json()["ack"] is True

    # 4. 종료
    res = client.post(f"/api/session/{sid}/stop")
    assert res.status_code == 200

    # 5. 종료 후 snapshot은 404
    res = client.get(f"/api/session/{sid}/snapshot")
    assert res.status_code == 404


def test_control_validation(client):
    res = client.post("/api/session/start", json={})
    sid = res.json()["sid"]

    # 범위를 벗어난 값 → 422
    bad = {**_initial_payload(), CONTROL_TAGS["igv"]: 999.0}
    res = client.post(f"/api/session/{sid}/control", json=bad)
    assert res.status_code == 422

    client.post(f"/api/session/{sid}/stop")


def test_websocket_stream(client):
    res = client.post("/api/session/start", json={})
    sid = res.json()["sid"]

    with client.websocket_connect(f"/api/session/{sid}/stream") as ws:
        # 첫 메시지: 초기 snapshot 또는 첫 step push
        msg = ws.receive_json()
        for key in ("sid", "t", "syngas_flow", "nox", "co", "flame_temp", "lambda", "power"):
            assert key in msg, f"missing key: {key}"
        assert msg["sid"] == sid

    client.post(f"/api/session/{sid}/stop")


def test_stop_unknown_sid_returns_ack(client):
    sid = str(uuid.uuid4())

    res = client.post(f"/api/session/{sid}/stop")

    assert res.status_code == 200
    assert res.json()["ack"] is True


def test_stop_is_idempotent(client):
    res = client.post("/api/session/start", json={})
    sid = res.json()["sid"]

    first = client.post(f"/api/session/{sid}/stop")
    second = client.post(f"/api/session/{sid}/stop")
    snapshot = client.get(f"/api/session/{sid}/snapshot")

    assert first.status_code == 200
    assert first.json()["ack"] is True
    assert second.status_code == 200
    assert second.json()["ack"] is True
    assert snapshot.status_code == 404


def test_prediction_endpoint(client):
    res = client.post("/api/prediction", json={"target_minutes": 5})
    assert res.status_code == 200
    body = res.json()
    for key in ("predicted_nox", "target_time", "threshold_exceeded", "threshold_value"):
        assert key in body


def test_sensor_endpoints(client):
    res = client.get("/api/sensor/latest")
    assert res.status_code == 200
    body = res.json()
    # DB 정의서 v1.0 컬럼명을 그대로 응답
    for key in ("measured_at", "nox_ppm", "syngas_flow", "generator_output"):
        assert key in body

    res = client.get("/api/sensor/history?limit=10")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    assert len(items) <= 10
