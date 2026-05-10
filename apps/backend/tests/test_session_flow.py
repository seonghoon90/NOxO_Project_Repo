"""세션 + control + WebSocket 통합 테스트.

프론트엔드가 실제로 따라가는 시나리오를 그대로 재현:
  start → control 변경 → WS로 push 받은 메시지에서 변화 확인 → stop.
"""

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
        CONTROL_TAGS["syngas"]: 1500.0,
        CONTROL_TAGS["igv"]: 75.0,
        CONTROL_TAGS["n2"]: 200.0,
        CONTROL_TAGS["n2_valve_1"]: 50.0,
        CONTROL_TAGS["syngas_srv"]: 60.0,
        CONTROL_TAGS["syngas_gcv_1"]: 55.0,
        CONTROL_TAGS["syngas_gcv_1a"]: 55.0,
        CONTROL_TAGS["syngas_gcv_2"]: 55.0,
        CONTROL_TAGS["ibh_valve"]: 30.0,
        CONTROL_TAGS["n2_flow"]: 100.0,
    }


def test_threshold_endpoint(client):
    res = client.get("/api/threshold")
    assert res.status_code == 200
    assert "nox_ppm_limit" in res.json()


def test_session_lifecycle(client):
    # 1. 세션 시작 (제어 10개 전체 전달)
    res = client.post("/api/session/start", json={"initial_condition": _initial_payload()})
    assert res.status_code == 200
    body = res.json()
    sid = body["sid"]
    assert sid

    # 2. snapshot 조회 — 10개 제어 변수 모두 포함되는지 확인
    res = client.get(f"/api/session/{sid}/snapshot")
    assert res.status_code == 200
    snap = res.json()
    assert snap["sid"] == sid
    for tag in CONTROL_TAGS.values():
        assert tag in snap["target"], f"missing target tag: {tag}"
        assert tag in snap["current"], f"missing current tag: {tag}"
    assert snap["target"][CONTROL_TAGS["syngas"]] == 1500.0
    assert snap["target"][CONTROL_TAGS["n2_flow"]] == 100.0
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

    # 기존 변수 범위 초과 → 422
    bad = {**_initial_payload(), CONTROL_TAGS["igv"]: 999.0}
    res = client.post(f"/api/session/{sid}/control", json=bad)
    assert res.status_code == 422

    # 신규 변수(개도 0~100) 범위 초과 → 422
    bad2 = {**_initial_payload(), CONTROL_TAGS["ibh_valve"]: 150.0}
    res = client.post(f"/api/session/{sid}/control", json=bad2)
    assert res.status_code == 422

    # 신규 변수(n2_flow 0~500) 범위 초과 → 422
    bad3 = {**_initial_payload(), CONTROL_TAGS["n2_flow"]: 9999.0}
    res = client.post(f"/api/session/{sid}/control", json=bad3)
    assert res.status_code == 422

    client.post(f"/api/session/{sid}/stop")


def test_websocket_stream(client):
    res = client.post("/api/session/start", json={})
    sid = res.json()["sid"]

    with client.websocket_connect(f"/api/session/{sid}/stream") as ws:
        msg = ws.receive_json()
        # 메타 + 제어 10 + 출력 — `DT_ARCHITECTURE.md §10` 평면 구조
        expected_keys = (
            "sid", "t",
            "syngas_flow", "igv_opening", "n2_offset",
            "n2_valve_1", "syngas_srv",
            "syngas_gcv_1", "syngas_gcv_1a", "syngas_gcv_2",
            "ibh_valve", "n2_flow",
            "nox", "exhaust_temp", "lambda", "power", "efficiency",
        )
        for key in expected_keys:
            assert key in msg, f"missing key: {key}"
        # `co`는 더 이상 송출되지 않음
        assert "co" not in msg
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
    # 5분 horizon 고정이므로 body는 sid만 (또는 빈 dict)
    res = client.post("/api/prediction", json={})
    assert res.status_code == 200
    body = res.json()
    for key in ("predicted_nox", "target_time", "threshold_exceeded", "threshold_value"):
        assert key in body


def test_prediction_endpoint_with_sid(client):
    # 활성 세션 기반 예측 — sid 전달
    start = client.post("/api/session/start", json={})
    sid = start.json()["sid"]

    res = client.post("/api/prediction", json={"sid": sid})
    assert res.status_code == 200
    body = res.json()
    assert "predicted_nox" in body

    client.post(f"/api/session/{sid}/stop")


def test_snapshot_includes_efficiency_excludes_co(client):
    res = client.post("/api/session/start", json={})
    sid = res.json()["sid"]

    snap = client.get(f"/api/session/{sid}/snapshot").json()
    assert "efficiency" in snap["output"]
    assert "co" not in snap["output"]

    client.post(f"/api/session/{sid}/stop")
