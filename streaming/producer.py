import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

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


def run_producer_loop(
    *,
    producer,
    topic: str,
    generator_factory: Callable[[], Iterable[dict]],
    interval_seconds: float,
    max_messages: int,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> int:
    """CSV 소진 시 처음으로 회귀하며 발행 루프 실행.

    `max_messages > 0`이면 N개 발행 후 즉시 종료(테스트/검증용 상한).
    `max_messages == 0`이면 SIGINT/예외로 중단될 때까지 무한 루프.

    반환값: 총 발행 메시지 수.
    """
    sent_count = 0
    loop_count = 0
    while True:
        loop_count += 1
        print(f"[Kafka Producer] loop #{loop_count} start")
        sent_in_loop = 0
        for message in generator_factory():
            message["published_at"] = (
                datetime.utcnow().isoformat(timespec="seconds") + "Z"
            )
            producer.send(topic, key=message["measured_at"], value=message)
            sent_count += 1
            sent_in_loop += 1
            print(f"[Kafka Producer] sent #{sent_count}: {message['measured_at']}")
            if max_messages and sent_count >= max_messages:
                return sent_count
            sleep_fn(interval_seconds)
        print(
            f"[Kafka Producer] loop #{loop_count} done — "
            f"sent_in_loop={sent_in_loop}, restarting from start"
        )


def main() -> None:
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(f"Kafka input CSV not found: {INPUT_FILE}")

    print(
        "[Kafka Producer] start "
        f"topic={TOPIC}, bootstrap={BOOTSTRAP_SERVERS}, input={INPUT_FILE}, "
        f"skip_bootstrap_minutes={BOOTSTRAP_MINUTES}, "
        f"max_messages={MAX_MESSAGES}, auto_loop={'on' if MAX_MESSAGES == 0 else 'off'}"
    )

    producer = build_producer()
    sent_total = 0
    try:
        sent_total = run_producer_loop(
            producer=producer,
            topic=TOPIC,
            generator_factory=lambda: iter_sensor_rows_after_bootstrap(
                INPUT_FILE, minutes=BOOTSTRAP_MINUTES
            ),
            interval_seconds=INTERVAL_SECONDS,
            max_messages=MAX_MESSAGES,
        )
    finally:
        producer.flush()
        producer.close()
        print(f"[Kafka Producer] done. sent={sent_total}")


if __name__ == "__main__":
    main()
