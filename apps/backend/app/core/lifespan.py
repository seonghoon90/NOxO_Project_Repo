"""애플리케이션 startup / shutdown.

- SensorBuffer (전역 deque, bootstrap 로드)
- KafkaSensorStream (메시지 → buffer.append)
- RealtimeEngine (1초 tick + 세션 순회)
- Simulator / Forecaster DI (실패 시 Stub 폴백)
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapters.forecaster import StubForecaster
from app.adapters.forecaster.ml import MLForecaster
from app.adapters.simulator import StubSimulator
from app.adapters.simulator.ml import MLSimulator
from app.config import get_settings
from app.core.kafka_stream import KafkaSensorStream
from app.core.logging import configure_logging
from app.core.realtime_engine import RealtimeEngine
from app.core.sensor_buffer import SensorBuffer
from app.core.session import Session
from app.core.ws_manager import WebSocketManager
from app.db.session import DbContext
from app.domain.tags import normalize_raw_message
from app.exceptions import PredictorUnavailableError
from app.repositories.simulation_log_repo import SimulationLogRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    DbContext.init(settings.database_url)

    # === Simulator DI ===
    if os.getenv("SIMULATOR_FALLBACK_STUB", "").lower() == "true":
        simulator = StubSimulator()
    else:
        try:
            simulator = MLSimulator()
        except PredictorUnavailableError as exc:
            logger.error("ml_simulator_unavailable err=%s", exc)
            if os.getenv("APP_ENV", "development") == "production":
                raise
            simulator = StubSimulator()

    # === Forecaster DI ===
    try:
        forecaster = MLForecaster()
    except PredictorUnavailableError as exc:
        logger.warning("ml_forecaster_unavailable err=%s — Stub fallback", exc)
        forecaster = StubForecaster()

    # === SimulationLogRepo (best-effort) ===
    simulation_log_repo: SimulationLogRepository | None = None
    if DbContext.is_available():
        try:
            simulation_log_repo = SimulationLogRepository(DbContext.session_factory)
            simulation_log_repo.ensure_tables()
        except Exception as exc:
            logger.warning("simulation_log_repo_unavailable err=%s", exc)

    # === SensorBuffer + KafkaSensorStream ===
    sensor_buffer = SensorBuffer(maxlen=900)
    kafka_sensor_stream = KafkaSensorStream(settings)

    # bootstrap 동기 로드 + 도메인 변환 적재
    kafka_sensor_stream.ensure_bootstrap_loaded()
    normalized_bootstrap = [
        normalize_raw_message(row["values"])
        for row in kafka_sensor_stream.bootstrap_rows
        if row.get("values")
    ]
    if normalized_bootstrap:
        sensor_buffer.load_bootstrap(normalized_bootstrap)
        logger.info("SensorBuffer bootstrap loaded rows=%d", len(normalized_bootstrap))
    else:
        logger.warning("SensorBuffer bootstrap empty — DT will use ffill fallback")

    kafka_sensor_stream.attach_buffer(sensor_buffer)

    # === Sessions + WS Manager ===
    sessions: dict[str, Session] = {}
    ws_manager = WebSocketManager()

    # === RealtimeEngine ===
    realtime_engine = RealtimeEngine(
        settings=settings,
        sensor_buffer=sensor_buffer,
        simulator=simulator,
        forecaster=forecaster,
        ws_manager=ws_manager,
        sessions=sessions,
    )

    app.state.settings = settings
    app.state.sensor_buffer = sensor_buffer
    app.state.sessions = sessions
    app.state.ws_manager = ws_manager
    app.state.simulator = simulator
    app.state.forecaster = forecaster
    app.state.kafka_sensor_stream = kafka_sensor_stream
    app.state.simulation_log_repo = simulation_log_repo
    app.state.realtime_engine = realtime_engine

    await kafka_sensor_stream.start()
    await realtime_engine.start()

    try:
        yield
    finally:
        await realtime_engine.stop()
        await kafka_sensor_stream.stop()
        DbContext.dispose()
