from __future__ import annotations

import csv
from datetime import datetime, timedelta
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
