from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from kafka import KafkaConsumer
from sqlalchemy import create_engine, text

from streaming.sensor_csv import load_bootstrap_rows, parse_measured_at


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_FILE = PROJECT_ROOT / "database" / "sensor_data_stream.sql"
TABLE_NAME = "sensor_data_stream"

DATABASE_URL = os.getenv("DATABASE_URL")
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
TOPIC = os.getenv("KAFKA_SENSOR_TOPIC", "noxo.sensor.raw")
GROUP_ID = os.getenv("KAFKA_ETL_CONSUMER_GROUP_ID", "noxo-stream-etl")
BOOTSTRAP_FILE = os.getenv("KAFKA_BOOTSTRAP_FILE")
BOOTSTRAP_MINUTES = int(os.getenv("KAFKA_BOOTSTRAP_MINUTES", "15"))
BOOTSTRAP_ENABLED = os.getenv("STREAM_ETL_BOOTSTRAP_ENABLED", "true").lower() == "true"
POLL_TIMEOUT_MS = int(os.getenv("KAFKA_ETL_CONSUMER_TIMEOUT_MS", "1000"))
RETRY_DELAY_SECONDS = int(os.getenv("STREAM_ETL_RETRY_DELAY_SECONDS", "5"))
AUTO_OFFSET_RESET = os.getenv("KAFKA_ETL_AUTO_OFFSET_RESET", "latest")

RAW_TO_DB_MAPPING = {
    "IGCC.CC.G1.ca_fqsg_cl": "syngas_flow",
    "IGCC.CC.G1.csgv": "igv_opening",
    "IGCC.CC.G1.NQKR3_MONITOR": "n2_offset",
    "IGCC.CC.G1.nicvs1": "n2_valve_1",
    "IGCC.CC.G1.FSAGR": "syngas_srv",
    "IGCC.CC.G1.FSAG11": "syngas_gcv_1",
    "IGCC.CC.G1.FSAG11A": "syngas_gcv_1a",
    "IGCC.CC.G1.FSAG12": "syngas_gcv_2",
    "IGCC.CC.G1.CSBHX": "ibh_valve",
    "IGCC.CC.G1.NQJ": "n2_flow",
    "IGCC.DeNOX.AT_H1_901_PV": "nox_ppm",
    "IGCC.CC.G1.TTXM": "exhaust_temp",
    "IGCC.CC.G1.DWATT": "power_mw",
    "IGCC.CC.G1.VNPR_P": "npr_primary",
}

DB_COLUMNS = list(RAW_TO_DB_MAPPING.values())


def get_database_url() -> str:
    if DATABASE_URL:
        return DATABASE_URL

    try:
        load_dotenv()
    except PermissionError:
        pass

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is required for stream ETL consumer")
    return database_url


def build_engine():
    return create_engine(get_database_url())


def read_sql_statements(sql_file: Path) -> list[str]:
    cleaned_lines: list[str] = []
    for line in sql_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        cleaned_lines.append(line)

    sql_text = "\n".join(cleaned_lines)
    return [statement.strip() for statement in sql_text.split(";") if statement.strip()]


def ensure_stream_table(engine) -> None:
    statements = read_sql_statements(SQL_FILE)
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def transform_message_to_row(
    message: dict,
    *,
    stream_topic: str,
    ingest_mode: str,
    kafka_partition: int | None = None,
    kafka_offset: int | None = None,
) -> dict:
    values = message.get("values") or {}
    row = {
        "measured_at": parse_measured_at(message["measured_at"]),
        "source_file": message.get("source", "unknown"),
        "stream_topic": stream_topic,
        "kafka_partition": kafka_partition,
        "kafka_offset": kafka_offset,
        "ingest_mode": ingest_mode,
    }

    missing_tags: list[str] = []
    for raw_tag, db_column in RAW_TO_DB_MAPPING.items():
        value = values.get(raw_tag)
        if value is None:
            missing_tags.append(raw_tag)
            continue
        row[db_column] = float(value)

    if missing_tags:
        raise ValueError(f"missing required tags: {missing_tags}")

    return row


def upsert_stream_row(engine, row: dict) -> None:
    sql = text(
        f"""
        INSERT INTO {TABLE_NAME} (
            measured_at,
            syngas_flow,
            igv_opening,
            n2_offset,
            n2_valve_1,
            syngas_srv,
            syngas_gcv_1,
            syngas_gcv_1a,
            syngas_gcv_2,
            ibh_valve,
            n2_flow,
            nox_ppm,
            exhaust_temp,
            power_mw,
            npr_primary,
            source_file,
            stream_topic,
            kafka_partition,
            kafka_offset,
            ingest_mode
        ) VALUES (
            :measured_at,
            :syngas_flow,
            :igv_opening,
            :n2_offset,
            :n2_valve_1,
            :syngas_srv,
            :syngas_gcv_1,
            :syngas_gcv_1a,
            :syngas_gcv_2,
            :ibh_valve,
            :n2_flow,
            :nox_ppm,
            :exhaust_temp,
            :power_mw,
            :npr_primary,
            :source_file,
            :stream_topic,
            :kafka_partition,
            :kafka_offset,
            :ingest_mode
        )
        ON CONFLICT (measured_at) DO UPDATE
        SET
            syngas_flow = EXCLUDED.syngas_flow,
            igv_opening = EXCLUDED.igv_opening,
            n2_offset = EXCLUDED.n2_offset,
            n2_valve_1 = EXCLUDED.n2_valve_1,
            syngas_srv = EXCLUDED.syngas_srv,
            syngas_gcv_1 = EXCLUDED.syngas_gcv_1,
            syngas_gcv_1a = EXCLUDED.syngas_gcv_1a,
            syngas_gcv_2 = EXCLUDED.syngas_gcv_2,
            ibh_valve = EXCLUDED.ibh_valve,
            n2_flow = EXCLUDED.n2_flow,
            nox_ppm = EXCLUDED.nox_ppm,
            exhaust_temp = EXCLUDED.exhaust_temp,
            power_mw = EXCLUDED.power_mw,
            npr_primary = EXCLUDED.npr_primary,
            source_file = EXCLUDED.source_file,
            stream_topic = EXCLUDED.stream_topic,
            kafka_partition = EXCLUDED.kafka_partition,
            kafka_offset = EXCLUDED.kafka_offset,
            ingest_mode = EXCLUDED.ingest_mode,
            ingested_at = CURRENT_TIMESTAMP
        """
    )
    with engine.begin() as conn:
        conn.execute(sql, row)


def bootstrap_stream_table(engine) -> int:
    if not BOOTSTRAP_ENABLED:
        return 0

    inserted = 0
    for message in load_bootstrap_rows(BOOTSTRAP_FILE, minutes=BOOTSTRAP_MINUTES):
        row = transform_message_to_row(
            message,
            stream_topic=TOPIC,
            ingest_mode="bootstrap",
        )
        upsert_stream_row(engine, row)
        inserted += 1
    return inserted


def build_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        auto_offset_reset=AUTO_OFFSET_RESET,
        enable_auto_commit=True,
        value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
        key_deserializer=lambda raw: raw.decode("utf-8") if raw else None,
        consumer_timeout_ms=POLL_TIMEOUT_MS,
    )


def run_consumer() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    engine = build_engine()
    ensure_stream_table(engine)

    bootstrap_count = bootstrap_stream_table(engine)
    logger.info(
        "stream_etl_bootstrap_done table=%s count=%s minutes=%s",
        TABLE_NAME,
        bootstrap_count,
        BOOTSTRAP_MINUTES,
    )

    while True:
        consumer = None
        try:
            consumer = build_consumer()
            logger.info(
                "stream_etl_consumer_started topic=%s bootstrap=%s group=%s auto_offset_reset=%s",
                TOPIC,
                BOOTSTRAP_SERVERS,
                GROUP_ID,
                AUTO_OFFSET_RESET,
            )
            for record in consumer:
                row = transform_message_to_row(
                    record.value,
                    stream_topic=record.topic,
                    kafka_partition=record.partition,
                    kafka_offset=record.offset,
                    ingest_mode="stream",
                )
                upsert_stream_row(engine, row)
        except KeyboardInterrupt:
            logger.info("stream_etl_consumer_stopped_by_user")
            break
        except Exception as exc:
            logger.warning("stream_etl_consumer_failed err=%s", exc)
            time.sleep(RETRY_DELAY_SECONDS)
        finally:
            if consumer is not None:
                consumer.close()


if __name__ == "__main__":
    run_consumer()
