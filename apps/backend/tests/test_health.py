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


def test_health_ml_ready_false_under_stub_fallback(client):
    """Stub fallback 모드(테스트 conftest는 patched_models_dir 없이 lifespan 진입 →
    MLSimulator 로드 실패 → APP_ENV != production → Stub로 회귀)에서 ml_ready=false."""
    res = client.get("/api/health")
    assert res.json()["ml_simulator_ready"] is False
