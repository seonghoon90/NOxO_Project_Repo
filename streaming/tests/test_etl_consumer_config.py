from __future__ import annotations

import importlib


def test_stream_etl_database_url_takes_precedence(monkeypatch):
    monkeypatch.setenv("STREAM_ETL_DATABASE_URL", "postgresql+psycopg://stream/db")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://legacy/db")

    import streaming.etl_consumer as etl_consumer

    importlib.reload(etl_consumer)

    assert etl_consumer.get_database_url() == "postgresql+psycopg://stream/db"


def test_database_url_can_be_built_from_postgres_components(monkeypatch):
    monkeypatch.delenv("STREAM_ETL_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "root")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_DB", "igcc_db")
    monkeypatch.setenv("STREAM_ETL_POSTGRES_HOST", "postgres")
    monkeypatch.setenv("STREAM_ETL_POSTGRES_PORT", "5432")

    import streaming.etl_consumer as etl_consumer

    importlib.reload(etl_consumer)

    assert (
        etl_consumer.get_database_url()
        == "postgresql+psycopg://root:secret@postgres:5432/igcc_db"
    )
