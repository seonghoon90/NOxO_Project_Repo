import json
import os
import time
from datetime import datetime
from pathlib import Path

from kafka import KafkaProducer

from streaming.sensor_csv import (
    DEFAULT_INPUT_FILE,
    iter_sensor_rows_after_bootstrap,
)

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
TOPIC = os.getenv("KAFKA_SENSOR_TOPIC", "noxo.sensor.raw")
INPUT_FILE = Path(os.getenv("KAFKA_INPUT_FILE", str(DEFAULT_INPUT_FILE)))
INTERVAL_SECONDS = float(os.getenv("KAFKA_PRODUCE_INTERVAL_SECONDS", "1"))
MAX_MESSAGES = int(os.getenv("KAFKA_MAX_MESSAGES", "0"))
BOOTSTRAP_MINUTES = int(os.getenv("KAFKA_BOOTSTRAP_MINUTES", "15"))


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
        f"topic={TOPIC}, bootstrap={BOOTSTRAP_SERVERS}, input={INPUT_FILE}, "
        f"skip_bootstrap_minutes={BOOTSTRAP_MINUTES}"
    )

    sent_count = 0
    producer = build_producer()
    try:
        for message in iter_sensor_rows_after_bootstrap(
            INPUT_FILE,
            minutes=BOOTSTRAP_MINUTES,
        ):
            message["published_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
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
