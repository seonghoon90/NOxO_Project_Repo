def test_streaming_latest_disabled_by_default(client):
    res = client.get("/api/streaming/latest")

    assert res.status_code == 200
    assert res.json() == {
        "enabled": False,
        "topic": "noxo.sensor.raw",
        "latest": None,
        "last_error": None,
    }
