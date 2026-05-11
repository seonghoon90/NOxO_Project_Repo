def test_health_status_ok(client):
    """기본 헬스 — status: ok."""
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"


def test_health_includes_ml_simulator_ready(client):
    """spec §7.7.4 — ml_simulator_ready bool 필드 노출."""
    res = client.get("/api/health")
    body = res.json()
    assert "ml_simulator_ready" in body
    assert isinstance(body["ml_simulator_ready"], bool)


def test_health_ml_ready_false_without_data_source(client, monkeypatch):
    """ML simulator만 있고 data_source가 없으면 ML 모드가 아니다."""
    monkeypatch.delenv("SIMULATOR_FALLBACK_STUB", raising=False)
    client.app.state.simulator = type("MLLike", (), {"name": "ml"})()
    client.app.state.data_source = None

    res = client.get("/api/health")
    assert res.json()["ml_simulator_ready"] is False


def test_health_ml_ready_false_under_env_stub_fallback(client, monkeypatch):
    """환경변수 fallback 강제 시에는 ML 구성요소가 있어도 false."""
    monkeypatch.setenv("SIMULATOR_FALLBACK_STUB", "true")
    client.app.state.simulator = type("MLLike", (), {"name": "ml"})()
    client.app.state.data_source = object()

    res = client.get("/api/health")
    assert res.json()["ml_simulator_ready"] is False


def test_health_ml_ready_true_with_ml_simulator_and_data_source(client, monkeypatch):
    """data_source + ML simulator가 모두 준비되면 true."""
    monkeypatch.delenv("SIMULATOR_FALLBACK_STUB", raising=False)
    client.app.state.simulator = type("MLLike", (), {"name": "ml"})()
    client.app.state.data_source = object()

    res = client.get("/api/health")
    assert res.json()["ml_simulator_ready"] is True
