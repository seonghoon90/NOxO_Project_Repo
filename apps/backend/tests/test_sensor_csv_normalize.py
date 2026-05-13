"""sensor_csv.normalize_measured_at — UTC ISO 8601 Z 정규화 회귀 (spec §2.2 L274)."""

from app.core.sensor_csv import normalize_measured_at


def test_normalize_naive_local_format_to_utc_z():
    """기본 bootstrap CSV 포맷 `%Y-%m-%d %H:%M:%S` → UTC Z."""
    assert (
        normalize_measured_at("2025-08-25 12:34:56")
        == "2025-08-25T12:34:56.000Z"
    )


def test_normalize_iso_with_z_passthrough():
    """이미 ISO 8601 + Z 포맷이면 millisecond precision으로 통일."""
    assert (
        normalize_measured_at("2025-08-25T12:34:56Z")
        == "2025-08-25T12:34:56.000Z"
    )


def test_normalize_iso_with_offset_converted_to_utc():
    """+09:00 offset → UTC 변환."""
    assert (
        normalize_measured_at("2025-08-25T21:34:56+09:00")
        == "2025-08-25T12:34:56.000Z"
    )


def test_normalize_none_or_empty_returns_none():
    assert normalize_measured_at(None) is None
    assert normalize_measured_at("") is None


def test_normalize_invalid_returns_none():
    """파싱 실패 시 None — envelope에서 wall-clock 폴백 트리거."""
    assert normalize_measured_at("not-a-timestamp") is None
