"""Simulation / forecast log persistence helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.schemas.prediction import PredictionResponse
from digital_twin.simulation import ControlVars


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SimulationLogRepository:
    def __init__(self, db_session_factory: sessionmaker[Session]):
        self.session_factory = db_session_factory

    def ensure_tables(self) -> None:
        ddl_statements = (
            """
            CREATE TABLE IF NOT EXISTS simulation_session_log (
                id BIGSERIAL PRIMARY KEY,
                sid VARCHAR(64) NOT NULL UNIQUE,
                started_at TIMESTAMP NOT NULL,
                ended_at TIMESTAMP,
                notes TEXT
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_session_started
            ON simulation_session_log (started_at DESC)
            """,
            """
            CREATE TABLE IF NOT EXISTS simulation_input_log (
                id BIGSERIAL PRIMARY KEY,
                sid VARCHAR(64) NOT NULL REFERENCES simulation_session_log(sid),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                syngas_flow DOUBLE PRECISION NOT NULL,
                igv_opening DOUBLE PRECISION NOT NULL,
                n2_offset DOUBLE PRECISION NOT NULL,
                n2_valve_1 DOUBLE PRECISION NOT NULL,
                syngas_srv DOUBLE PRECISION NOT NULL,
                syngas_gcv_1 DOUBLE PRECISION NOT NULL,
                syngas_gcv_1a DOUBLE PRECISION NOT NULL,
                syngas_gcv_2 DOUBLE PRECISION NOT NULL,
                ibh_valve DOUBLE PRECISION NOT NULL,
                n2_flow DOUBLE PRECISION NOT NULL
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_sim_input_sid_created
            ON simulation_input_log (sid, created_at DESC)
            """,
            """
            CREATE TABLE IF NOT EXISTS forecast_log (
                id BIGSERIAL PRIMARY KEY,
                sid VARCHAR(64) REFERENCES simulation_session_log(sid),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                target_time TIMESTAMP NOT NULL,
                predicted_nox DOUBLE PRECISION NOT NULL,
                threshold_value DOUBLE PRECISION NOT NULL,
                threshold_exceeded BOOLEAN NOT NULL
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_forecast_sid_created
            ON forecast_log (sid, created_at DESC)
            """,
        )
        with self.session_factory() as session:
            for ddl in ddl_statements:
                session.execute(text(ddl))
            session.commit()

    def create_session_log(
        self,
        sid: str,
        started_at: datetime | None = None,
        notes: str | None = None,
    ) -> None:
        sql = text(
            """
            INSERT INTO simulation_session_log (sid, started_at, notes)
            VALUES (:sid, :started_at, :notes)
            """
        )
        with self.session_factory() as session:
            session.execute(
                sql,
                {
                    "sid": sid,
                    "started_at": started_at or utcnow_naive(),
                    "notes": notes,
                },
            )
            session.commit()

    def finish_session_log(self, sid: str, ended_at: datetime | None = None) -> None:
        sql = text(
            """
            UPDATE simulation_session_log
            SET ended_at = :ended_at
            WHERE sid = :sid AND ended_at IS NULL
            """
        )
        with self.session_factory() as session:
            session.execute(
                sql,
                {"sid": sid, "ended_at": ended_at or utcnow_naive()},
            )
            session.commit()

    def create_input_log(
        self,
        sid: str,
        controls: ControlVars,
        created_at: datetime | None = None,
    ) -> None:
        sql = text(
            """
            INSERT INTO simulation_input_log (
                sid,
                created_at,
                syngas_flow,
                igv_opening,
                n2_offset,
                n2_valve_1,
                syngas_srv,
                syngas_gcv_1,
                syngas_gcv_1a,
                syngas_gcv_2,
                ibh_valve,
                n2_flow
            ) VALUES (
                :sid,
                :created_at,
                :syngas_flow,
                :igv_opening,
                :n2_offset,
                :n2_valve_1,
                :syngas_srv,
                :syngas_gcv_1,
                :syngas_gcv_1a,
                :syngas_gcv_2,
                :ibh_valve,
                :n2_flow
            )
            """
        )
        with self.session_factory() as session:
            session.execute(
                sql,
                {
                    "sid": sid,
                    "created_at": created_at or utcnow_naive(),
                    "syngas_flow": controls.syngas_flow,
                    "igv_opening": controls.igv_opening,
                    "n2_offset": controls.n2_offset,
                    "n2_valve_1": controls.n2_valve_1,
                    "syngas_srv": controls.syngas_srv,
                    "syngas_gcv_1": controls.syngas_gcv_1,
                    "syngas_gcv_1a": controls.syngas_gcv_1a,
                    "syngas_gcv_2": controls.syngas_gcv_2,
                    "ibh_valve": controls.ibh_valve,
                    "n2_flow": controls.n2_flow,
                },
            )
            session.commit()

    def create_forecast_log(
        self,
        response: PredictionResponse,
        sid: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        sql = text(
            """
            INSERT INTO forecast_log (
                sid,
                created_at,
                target_time,
                predicted_nox,
                threshold_value,
                threshold_exceeded
            ) VALUES (
                :sid,
                :created_at,
                :target_time,
                :predicted_nox,
                :threshold_value,
                :threshold_exceeded
            )
            """
        )
        with self.session_factory() as session:
            session.execute(
                sql,
                {
                    "sid": sid,
                    "created_at": created_at or utcnow_naive(),
                    "target_time": response.target_time.replace(tzinfo=None),
                    "predicted_nox": response.predicted_nox,
                    "threshold_value": response.threshold_value,
                    "threshold_exceeded": response.threshold_exceeded,
                },
            )
            session.commit()
