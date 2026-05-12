import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator

from kafka import KafkaProducer


PROJECT_ROOT = Path(os.getenv("NOXO_PROJECT_ROOT", Path(__file__).resolve().parents[1]))
DEFAULT_INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "250811-250825" / "NOx_test_20250825.csv"

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
TOPIC = os.getenv("KAFKA_SENSOR_TOPIC", "noxo.sensor.raw")
INPUT_FILE = Path(os.getenv("KAFKA_INPUT_FILE", str(DEFAULT_INPUT_FILE)))
INTERVAL_SECONDS = float(os.getenv("KAFKA_PRODUCE_INTERVAL_SECONDS", "1"))
MAX_MESSAGES = int(os.getenv("KAFKA_MAX_MESSAGES", "0"))


def parse_value(value: str) -> str | float | None:
    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return value


def iter_sensor_rows(input_file: Path) -> Iterator[dict]:
    with input_file.open(newline="", encoding="utf-8-sig") as csv_file:
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
                "source": input_file.name,
                "measured_at": measured_at,
                "published_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "values": values,
            }


def build_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda message: json.dumps(message).encode("utf-8"),
        key_serializer=lambda key: key.encode("utf-8"),
    )


def main() -> None:
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(f"Kafka input CSV not found: {INPUT_FILE}")

    print(
        "[Kafka Producer] start "
        f"topic={TOPIC}, bootstrap={BOOTSTRAP_SERVERS}, input={INPUT_FILE}"
    )

    sent_count = 0
    producer = build_producer()
    try:
        for message in iter_sensor_rows(INPUT_FILE):
            producer.send(
                TOPIC,
                key=message["measured_at"],
                value=message,
            )
            sent_count += 1
            print(f"[Kafka Producer] sent #{sent_count}: {message['measured_at']}")

            if MAX_MESSAGES and sent_count >= MAX_MESSAGES:
                break

            time.sleep(INTERVAL_SECONDS)
    finally:
        producer.flush()
        producer.close()
        print(f"[Kafka Producer] done. sent={sent_count}")


if __name__ == "__main__":
    main()
