from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core.sensor_buffer import SensorBuffer
from app.core.sensor_csv import iter_sensor_rows_after_bootstrap
from app.config import get_settings
from app.main import create_app


def _write_stream_csv(path: Path, total_rows: int = 10) -> None:
    lines = ["TagName,Column1,IGCC.CC.G1.csgv"]
    for second in range(total_rows):
        timestamp = f"2025-08-25 00:00:{second:02d}"
        lines.append(f"{timestamp},,{70 + second}")
    path.write_text("\n".join(lines), encoding="utf-8")


def test_streaming_latest_disabled_by_default(client):
    res = client.get("/api/streaming/latest")

    assert res.status_code == 200
    assert res.json() == {
        "enabled": False,
        "topic": "noxo.sensor.raw",
        "latest": None,
        "last_error": None,
    }


def test_streaming_bootstrap_returns_preloaded_rows(monkeypatch, tmp_path):
    bootstrap_file = tmp_path / "stream.csv"
    _write_stream_csv(bootstrap_file)

    monkeypatch.setenv("KAFKA_BOOTSTRAP_FILE", str(bootstrap_file))
    monkeypatch.setenv("KAFKA_BOOTSTRAP_MINUTES", "1")
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/streaming/bootstrap")

    get_settings.cache_clear()

    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is False
    assert body["minutes"] == 1
    assert body["source"] == "stream.csv"
    assert body["count"] == 6
    assert len(body["rows"]) == 6
    assert body["rows"][0]["measured_at"] == "2025-08-25 00:00:04"
    assert body["rows"][-1]["measured_at"] == "2025-08-25 00:00:09"
    assert body["error"] is None


def test_iter_sensor_rows_after_bootstrap_skips_preload_window(tmp_path):
    bootstrap_file = tmp_path / "stream.csv"
    lines = ["TagName,Column1,IGCC.CC.G1.csgv"]
    for second in range(70):
        minute = second // 60
        sec = second % 60
        lines.append(f"2025-08-25 00:{minute:02d}:{sec:02d},,{70 + second}")
    bootstrap_file.write_text("\n".join(lines), encoding="utf-8")

    rows = list(iter_sensor_rows_after_bootstrap(bootstrap_file, minutes=1))

    assert rows
    assert rows[0]["measured_at"] == "2025-08-25 00:01:04"


def test_ensure_bootstrap_loaded_idempotent(settings_with_csv, tmp_path):
    """ensure_bootstrap_loaded는 여러 번 호출해도 1회만 로드한다."""
    from app.core.kafka_stream import KafkaSensorStream

    bootstrap_file = tmp_path / "stream.csv"
    lines = ["TagName,Column1,IGCC.CC.G1.csgv"]
    for second in range(120):
        minute = second // 60
        sec = second % 60
        lines.append(f"2025-08-25 00:{minute:02d}:{sec:02d},,{70 + second}")
    bootstrap_file.write_text("\n".join(lines), encoding="utf-8")
    settings_with_csv.kafka_bootstrap_file = str(bootstrap_file)
    settings_with_csv.kafka_bootstrap_minutes = 1

    stream = KafkaSensorStream(settings_with_csv)
    stream.ensure_bootstrap_loaded()
    first = list(stream.bootstrap_rows)
    stream.ensure_bootstrap_loaded()
    second_load = list(stream.bootstrap_rows)
    assert first == second_load
    assert len(first) > 0


def test_attach_buffer_routes_messages(settings_with_csv):
    """attach_buffer 후 normalize → buffer.append 경로가 활성화된다."""
    from app.core.kafka_stream import KafkaSensorStream

    stream = KafkaSensorStream(settings_with_csv)
    buffer = SensorBuffer(maxlen=10)
    stream.attach_buffer(buffer)

    fake_record = MagicMock()
    fake_record.value = {
        "source": "test",
        "measured_at": "2025-08-25 00:00:00",
        "values": {"IGCC.CC.G1.ca_fqsg_cl": 100.5},
    }
    stream._route_record(fake_record)

    assert len(buffer) == 1
    # measured_at은 정규화된 row와 함께 보존(RealtimeEngine이 kafka_latest.ts로 사용).
    assert buffer.latest_row() == {
        "syngas_flow": 100.5,
        "measured_at": "2025-08-25 00:00:00",
    }


def test_route_record_without_buffer_does_nothing(settings_with_csv):
    """attach_buffer 안 한 상태에서는 buffer 없이도 안전하게 동작."""
    from app.core.kafka_stream import KafkaSensorStream

    stream = KafkaSensorStream(settings_with_csv)
    fake_record = MagicMock()
    fake_record.value = {"source": "x", "measured_at": "t", "values": {}}
    stream._route_record(fake_record)
