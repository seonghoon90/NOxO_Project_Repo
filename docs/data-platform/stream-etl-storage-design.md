# Stream ETL Storage Design

## Why `sensor_data_stream` should be separate

`NOx_train_20250811_20250824.csv` and `NOx_test_20250825.csv` come from the same source family and share the same business schema.

But their roles are now different.

- `sensor_data`
  - historical/train dataset
  - batch ETL target
  - baseline reference data for backend and model workflow
- `sensor_data_stream`
  - Kafka simulation dataset
  - stream ETL target
  - bootstrap + live replay storage for test-day data

Because `NOx_test_20250825.csv` is no longer just a holdout file and is now used as streaming simulation input, separating its storage makes the architecture easier to explain and safer to operate.

## Design principle

Keep the same 14 business columns as `sensor_data`, but store them in a separate table with stream lineage metadata.

This gives us:

1. same operational schema for frontend/backend/model usage
2. separate lifecycle for historical data and replayed stream data
3. easier debug and audit for Kafka bootstrap/live ingestion
4. cleaner portfolio explanation:
   - raw topic
   - stream ETL consumer
   - PostgreSQL stream table

## Recommended table

Table name:

- `sensor_data_stream`

Main idea:

- business columns match `sensor_data`
- extra metadata columns record where and how the row arrived

## Column groups

### 1. Business columns

These should match `sensor_data` exactly.

- `measured_at`
- `syngas_flow`
- `igv_opening`
- `n2_offset`
- `n2_valve_1`
- `syngas_srv`
- `syngas_gcv_1`
- `syngas_gcv_1a`
- `syngas_gcv_2`
- `ibh_valve`
- `n2_flow`
- `nox_ppm`
- `exhaust_temp`
- `power_mw`
- `npr_primary`

### 2. Stream lineage columns

These are specific to the streaming pipeline.

- `source_file`
  - example: `NOx_test_20250825.csv`
- `stream_topic`
  - example: `noxo.sensor.raw`
- `kafka_partition`
- `kafka_offset`
- `ingest_mode`
  - `bootstrap` or `stream`
- `ingested_at`
  - actual DB insert time

## Why not write directly into `sensor_data`

If we write replayed Kafka data into `sensor_data` directly:

- train/historical and replay/test meanings get mixed
- bootstrap and live replay can create duplicates more easily
- operational validation becomes harder
- it becomes less clear whether a row came from batch ETL or stream ETL

## Recommended uniqueness strategy

Use:

- unique on `measured_at`
- unique on `(stream_topic, kafka_partition, kafka_offset)`

Why:

- `measured_at` is the business key for this replay dataset
- topic/partition/offset is the Kafka lineage key
- both help protect against duplicate ingestion

## Recommended insert behavior

The stream ETL consumer should use upsert.

Recommended rule:

- `ON CONFLICT (measured_at) DO UPDATE`

Why:

- bootstrap rows may be inserted first
- later stream replay may encounter the same business timestamp
- we want deterministic final state instead of duplicate rows

## Suggested ETL flow

```text
NOx_test_20250825.csv
-> Producer
-> noxo.sensor.raw
-> stream_etl_consumer
-> tag mapping / type cast / validation
-> sensor_data_stream
```

## Transformation rule

The ETL consumer should:

1. read Kafka message
2. extract `measured_at`
3. map raw tag names to DB column names
4. cast all required numeric fields
5. reject rows with missing required fields
6. write to `sensor_data_stream`

## Mapping rule

Use the same mapping already used in batch ETL for `sensor_data`.

| Raw Tag | Stream DB column |
| :--- | :--- |
| `IGCC.CC.G1.ca_fqsg_cl` | `syngas_flow` |
| `IGCC.CC.G1.csgv` | `igv_opening` |
| `IGCC.CC.G1.NQKR3_MONITOR` | `n2_offset` |
| `IGCC.CC.G1.nicvs1` | `n2_valve_1` |
| `IGCC.CC.G1.FSAGR` | `syngas_srv` |
| `IGCC.CC.G1.FSAG11` | `syngas_gcv_1` |
| `IGCC.CC.G1.FSAG11A` | `syngas_gcv_1a` |
| `IGCC.CC.G1.FSAG12` | `syngas_gcv_2` |
| `IGCC.CC.G1.CSBHX` | `ibh_valve` |
| `IGCC.CC.G1.NQJ` | `n2_flow` |
| `IGCC.DeNOX.AT_H1_901_PV` | `nox_ppm` |
| `IGCC.CC.G1.TTXM` | `exhaust_temp` |
| `IGCC.CC.G1.DWATT` | `power_mw` |
| `IGCC.CC.G1.VNPR_P` | `npr_primary` |

## Bootstrap relation

The initial 15-minute preload should also be able to enter `sensor_data_stream`.

Recommended interpretation:

- preload insert rows with `ingest_mode='bootstrap'`
- Kafka replay insert rows with `ingest_mode='stream'`

That way we can trace whether a row first arrived from preload or from live replay.

## DDL draft location

The concrete SQL draft is in:

- `database/sensor_data_stream.sql`

## Current implementation draft

The first implementation draft uses a dedicated streaming worker:

- `streaming/etl_consumer.py`

It does four things:

1. ensure `sensor_data_stream` exists
2. optionally preload the first 15 minutes into `sensor_data_stream`
3. consume Kafka messages from `noxo.sensor.raw`
4. upsert transformed rows into PostgreSQL

## Consumer runtime config

Important environment variables:

- `DATABASE_URL`
- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_SENSOR_TOPIC`
- `KAFKA_ETL_CONSUMER_GROUP_ID`
- `KAFKA_BOOTSTRAP_FILE`
- `KAFKA_BOOTSTRAP_MINUTES`
- `STREAM_ETL_BOOTSTRAP_ENABLED`
- `KAFKA_ETL_CONSUMER_TIMEOUT_MS`
- `STREAM_ETL_RETRY_DELAY_SECONDS`

## Compose service

The Docker compose service name is:

- `kafka-etl-consumer`

Location:

- `docker/docker-compose.kafka.yml`

## Recommended local flow

```text
redpanda up
-> kafka-etl-consumer up
-> kafka-producer run
-> sensor_data_stream insert check
```

## Recommended EC2 flow

```text
redpanda up
-> backend up
-> kafka-etl-consumer up
-> kafka-producer run
-> bootstrap/latest API check
-> sensor_data_stream row check
```

## Next implementation step

1. confirm the table name and DDL with the DB/backend team
2. verify `stream_etl_consumer.py` against local or EC2 PostgreSQL
3. confirm bootstrap rows and live stream rows both land in `sensor_data_stream`
4. verify EC2 end to end:
   - bootstrap insert
   - live Kafka insert
   - DB row count and time range
