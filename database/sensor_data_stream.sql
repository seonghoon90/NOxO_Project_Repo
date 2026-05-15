-- sensor_data_stream DDL draft
-- Purpose:
--   Store Kafka simulation data from NOx_test_20250825.csv after ETL/transform.
--   Keep it separate from historical train data in sensor_data.

CREATE TABLE IF NOT EXISTS sensor_data_stream (
    id BIGSERIAL PRIMARY KEY,

    -- business timestamp from the original sensor row
    measured_at TIMESTAMP NOT NULL,

    -- same 14 operational columns as sensor_data
    syngas_flow DOUBLE PRECISION NOT NULL,
    igv_opening DOUBLE PRECISION NOT NULL,
    n2_offset DOUBLE PRECISION NOT NULL,
    n2_valve_1 DOUBLE PRECISION NOT NULL,
    syngas_srv DOUBLE PRECISION NOT NULL,
    syngas_gcv_1 DOUBLE PRECISION NOT NULL,
    syngas_gcv_1a DOUBLE PRECISION NOT NULL,
    syngas_gcv_2 DOUBLE PRECISION NOT NULL,
    ibh_valve DOUBLE PRECISION NOT NULL,
    n2_flow DOUBLE PRECISION NOT NULL,
    nox_ppm DOUBLE PRECISION NOT NULL,
    exhaust_temp DOUBLE PRECISION NOT NULL,
    power_mw DOUBLE PRECISION NOT NULL,
    npr_primary DOUBLE PRECISION NOT NULL,
    -- optional O2 value for NOx 15% O2 display correction
    o2_pct DOUBLE PRECISION,

    -- stream lineage / audit columns
    source_file VARCHAR(255) NOT NULL,
    stream_topic VARCHAR(128) NOT NULL,
    kafka_partition INTEGER,
    kafka_offset BIGINT,
    ingest_mode VARCHAR(16) NOT NULL,
    ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_sensor_data_stream_measured_at UNIQUE (measured_at),
    CONSTRAINT uq_sensor_data_stream_topic_offset UNIQUE (stream_topic, kafka_partition, kafka_offset),
    CONSTRAINT chk_sensor_data_stream_ingest_mode
        CHECK (ingest_mode IN ('bootstrap', 'stream'))
);

ALTER TABLE sensor_data_stream
    ADD COLUMN IF NOT EXISTS o2_pct DOUBLE PRECISION;

CREATE INDEX IF NOT EXISTS idx_sensor_data_stream_measured_at
    ON sensor_data_stream (measured_at DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_data_stream_ingested_at
    ON sensor_data_stream (ingested_at DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_data_stream_ingest_mode_measured_at
    ON sensor_data_stream (ingest_mode, measured_at DESC);

-- Recommended upsert pattern for ETL consumer:
--
-- INSERT INTO sensor_data_stream (...)
-- VALUES (...)
-- ON CONFLICT (measured_at) DO UPDATE
-- SET
--     syngas_flow = EXCLUDED.syngas_flow,
--     igv_opening = EXCLUDED.igv_opening,
--     n2_offset = EXCLUDED.n2_offset,
--     n2_valve_1 = EXCLUDED.n2_valve_1,
--     syngas_srv = EXCLUDED.syngas_srv,
--     syngas_gcv_1 = EXCLUDED.syngas_gcv_1,
--     syngas_gcv_1a = EXCLUDED.syngas_gcv_1a,
--     syngas_gcv_2 = EXCLUDED.syngas_gcv_2,
--     ibh_valve = EXCLUDED.ibh_valve,
--     n2_flow = EXCLUDED.n2_flow,
--     nox_ppm = EXCLUDED.nox_ppm,
--     exhaust_temp = EXCLUDED.exhaust_temp,
--     power_mw = EXCLUDED.power_mw,
--     npr_primary = EXCLUDED.npr_primary,
--     source_file = EXCLUDED.source_file,
--     stream_topic = EXCLUDED.stream_topic,
--     kafka_partition = EXCLUDED.kafka_partition,
--     kafka_offset = EXCLUDED.kafka_offset,
--     ingest_mode = EXCLUDED.ingest_mode,
--     o2_pct = EXCLUDED.o2_pct,
--     ingested_at = CURRENT_TIMESTAMP;
