"""Kafka-compatible sensor stream consumer.

The consumer is optional and disabled by default. It keeps only the latest
message in memory so the first streaming milestone stays simple.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from datetime import datetime
from typing import Any

from app.config import Settings

logger = logging.getLogger(__name__)


class KafkaSensorStream:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._latest: dict[str, Any] | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None
        self._last_error: str | None = None

    @property
    def enabled(self) -> bool:
        return self._settings.kafka_stream_enabled

    @property
    def latest(self) -> dict[str, Any] | None:
        return self._latest

    @property
    def topic(self) -> str:
        return self._settings.kafka_sensor_topic

    @property
    def last_error(self) -> str | None:
        return self._last_error

    async def start(self) -> None:
        if not self.enabled or self._task is not None:
            return

        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._consume_forever())
        logger.info(
            "Kafka sensor stream enabled. topic=%s bootstrap=%s",
            self._settings.kafka_sensor_topic,
            self._settings.kafka_bootstrap_servers,
        )

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()

        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

        self._task = None
        self._stop_event = None

    async def _consume_forever(self) -> None:
        while self._stop_event is not None and not self._stop_event.is_set():
            try:
                await asyncio.to_thread(self._consume_until_stopped)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - broker integration path
                self._last_error = str(exc)
                logger.warning("Kafka sensor stream consumer failed: %s", exc)
                await asyncio.sleep(5)

    def _consume_until_stopped(self) -> None:
        from kafka import KafkaConsumer

        consumer = KafkaConsumer(
            self._settings.kafka_sensor_topic,
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            group_id=self._settings.kafka_consumer_group_id,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
            key_deserializer=lambda raw: raw.decode("utf-8") if raw else None,
            consumer_timeout_ms=1000,
        )

        try:
            while self._stop_event is not None and not self._stop_event.is_set():
                for record in consumer:
                    self._latest = {
                        "topic": record.topic,
                        "partition": record.partition,
                        "offset": record.offset,
                        "key": record.key,
                        "received_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                        "message": record.value,
                    }
                    self._last_error = None

                    if self._stop_event is not None and self._stop_event.is_set():
                        break
        finally:
            consumer.close()
