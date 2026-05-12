"""애플리케이션 startup / shutdown 훅.

- 모든 singleton 컴포넌트(StateStore, InputInjector, WSManager, SimLoop, Predictor)를
  app.state에 attach.
- DB engine 초기화/dispose.
- shutdown 시 sim loop 전체 취소.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapters.data_source import SnapshotDataSource
from app.adapters.forecaster import StubForecaster
from app.adapters.simulator import StubSimulator
from app.adapters.simulator.ml import MLSimulator
from app.config import get_settings
from app.core.input_injector import InputInjector
from app.core.kafka_stream import KafkaSensorStream
from app.core.logging import configure_logging
from app.core.session_context import SessionContext
from app.core.sim_loop import SimLoopManager
from app.core.state_store import InMemoryStateStore
from app.core.ws_manager import WebSocketManager
from app.db.session import DbContext
from app.exceptions import DataSourceUnavailableError, PredictorUnavailableError
from app.repositories.sensor_repo import SensorRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    DbContext.init(settings.database_url)

    state_store = InMemoryStateStore()
    injector = InputInjector()
    ws_manager = WebSocketManager()
    # 두 어댑터 별도 DI 슬롯 — `BACKEND_ARCHITECTURE.md §10`
    # === Simulator DI — B5 환경 변수 + ML 우선 ===
    if os.getenv("SIMULATOR_FALLBACK_STUB", "").lower() == "true":
        simulator = StubSimulator()
    else:
        try:
            simulator = MLSimulator()
        except PredictorUnavailableError as e:
            logger.error("ml_model_unavailable err=%s", e)
            if os.getenv("APP_ENV", "development") == "production":
                raise
            simulator = StubSimulator()
    forecaster = StubForecaster()
    kafka_sensor_stream = KafkaSensorStream(settings)

    # === session_contexts + DataSource (B안 ML 모드) ===
    session_contexts: dict[str, SessionContext] = {}
    data_source = None
    if DbContext.is_available():
        if (
            settings.sensor_column_mapping is None
            and os.getenv("APP_ENV", "development").lower() == "production"
        ):
            raise DataSourceUnavailableError(
                "SENSOR_COLUMN_MAPPING is required for production ML snapshot mode"
            )
        sensor_repo = SensorRepository(
            db_session_factory=DbContext.session_factory,
            tag_to_db_column=settings.sensor_column_mapping,
        )
        data_source = SnapshotDataSource(sensor_repo)
    else:
        logger.warning("DB not configured — B안 ML 모드 비활성 (StubSimulator 회귀)")

    # === A1 (5차 보강) — 회귀 모드 invariant ===
    if data_source is None and not isinstance(simulator, StubSimulator):
        logger.warning(
            "ml_simulator_without_datasource — forcing StubSimulator (data_source=None invariant)"
        )
        simulator = StubSimulator()
    sim_loop = SimLoopManager(
        settings=settings,
        state_store=state_store,
        injector=injector,
        ws_manager=ws_manager,
        simulator=simulator,
        session_contexts=session_contexts,
    )

    app.state.settings = settings
    app.state.state_store = state_store
    app.state.input_injector = injector
    app.state.ws_manager = ws_manager
    app.state.simulator = simulator
    app.state.forecaster = forecaster
    app.state.kafka_sensor_stream = kafka_sensor_stream
    app.state.sim_loop = sim_loop
    app.state.data_source = data_source
    app.state.session_contexts = session_contexts

    await kafka_sensor_stream.start()

    try:
        yield
    finally:
        await kafka_sensor_stream.stop()
        await sim_loop.stop_all()
        DbContext.dispose()
