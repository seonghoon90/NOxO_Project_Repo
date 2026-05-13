from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator


DEFAULT_INPUT_FILE = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "raw"
    / "250811-250825"
    / "NOx_test_20250825.csv"
)
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def resolve_input_file(input_file: str | Path | None = None) -> Path:
    if input_file is None:
        return DEFAULT_INPUT_FILE
    return Path(input_file)


def parse_value(value: str) -> str | float | None:
    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return value


def parse_measured_at(value: str) -> datetime:
    return datetime.strptime(value, TIMESTAMP_FORMAT)


def normalize_measured_at(value: str | None) -> str | None:
    """measured_at을 UTC ISO 8601 + Z로 정규화 (spec §2.2 L274).

    이미 ISO 8601 + Z 또는 +00:00이면 그대로 통과, naive `"%Y-%m-%d %H:%M:%S"`는
    UTC로 간주해 변환. 파싱 실패 시 None 반환(envelope에서 wall-clock 폴백).
    """
    if not value:
        return None
    try:
        # ISO 8601(Z 포함) 우선
        if value.endswith("Z"):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif "T" in value or "+" in value:
            dt = datetime.fromisoformat(value)
        else:
            dt = datetime.strptime(value, TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def iter_sensor_rows(input_file: str | Path | None = None) -> Iterator[dict]:
    resolved = resolve_input_file(input_file)
    with resolved.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row_index, row in enumerate(reader):
            if row_index < 4:
                continue

            measured_at = row["TagName"]
            values = {
                key: parse_value(value)
                for key, value in row.items()
                if key and key not in {"TagName", "Column1"}
            }
            yield {
                "source": resolved.name,
                "measured_at": measured_at,
                "values": values,
            }


def load_bootstrap_rows(
    input_file: str | Path | None = None,
    minutes: int = 15,
) -> list[dict]:
    rows = list(iter_sensor_rows(input_file))
    if not rows or minutes <= 0:
        return []

    start_at = parse_measured_at(rows[0]["measured_at"])
    cutoff = start_at + timedelta(minutes=minutes)
    return [
        row
        for row in rows
        if parse_measured_at(row["measured_at"]) < cutoff
    ]


def iter_sensor_rows_after_bootstrap(
    input_file: str | Path | None = None,
    minutes: int = 0,
) -> Iterator[dict]:
    rows = iter_sensor_rows(input_file)
    if minutes <= 0:
        yield from rows
        return

    buffered = list(rows)
    if not buffered:
        return

    start_at = parse_measured_at(buffered[0]["measured_at"])
    cutoff = start_at + timedelta(minutes=minutes)
    for row in buffered:
        if parse_measured_at(row["measured_at"]) >= cutoff:
            yield row
