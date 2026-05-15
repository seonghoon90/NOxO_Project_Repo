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
from app.core.sensor_buffer import SensorBuffer, operating_point_to_sensor_row
from app.core.sensor_csv import normalize_measured_at
from app.core.sensor_stream_poller import SensorStreamPoller
from app.core.session import Session
from app.core.ws_manager import WebSocketManager
from app.db.session import DbContext
from app.domain.tags import normalize_raw_message
from app.exceptions import PredictorUnavailableError
from app.repositories.sensor_stream_repo import SensorStreamRepository
from app.repositories.simulation_log_repo import SimulationLogRepository
from app.adapters.container_restart import (
    ContainerRestartAdapter,
    DockerSocketAdapter,
    NoopRestartAdapter,
)
from app.services.reset_service import ResetService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    # 조기 검증 — 무거운 init(ML 모델·KafkaProducer·CSV bootstrap)을 시작하기 전에
    # 환경변수 정합성을 먼저 거른다. 잘못된 조합은 startup 수 초 낭비 없이 즉시 fail.
    if settings.sensor_stream_poll_enabled:
        if settings.kafka_stream_enabled:
            raise RuntimeError(
                "SENSOR_STREAM_POLL_ENABLED와 KAFKA_STREAM_ENABLED는 동시 활성화 불가 — "
                "둘 다 SensorBuffer에 쓰면 중복 row가 들어간다."
            )
        if not settings.database_url:
            raise RuntimeError(
                "SENSOR_STREAM_POLL_ENABLED=true는 DATABASE_URL 설정 필수 — "
                "silent disable 대신 명시적 fail."
            )

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

    # bootstrap 동기 로드 + 도메인 변환 적재 (measured_at 보존)
    kafka_sensor_stream.ensure_bootstrap_loaded()
    normalized_bootstrap = []
    for row in kafka_sensor_stream.bootstrap_rows:
        values = row.get("values")
        if not values:
            continue
        normalized = normalize_raw_message(values)
        if not normalized:
            continue
        # spec §2.2 L274 — UTC ISO 8601 + Z로 정규화한 뒤 적재.
        measured_at = normalize_measured_at(row.get("measured_at"))
        if measured_at is not None:
            normalized = {**normalized, "measured_at": measured_at}
        normalized_bootstrap.append(normalized)
    if normalized_bootstrap:
        sensor_buffer.load_bootstrap(normalized_bootstrap)
        logger.info("SensorBuffer bootstrap loaded rows=%d", len(normalized_bootstrap))
    else:
        # bootstrap 실패 시 dt_config.operating_point로 기본 row 1개 주입.
        # SessionContext.from_sensor_buffer가 ValueError를 던지지 않도록 보장.
        sensor_buffer.load_bootstrap([operating_point_to_sensor_row()])
        logger.warning(
            "SensorBuffer bootstrap empty — injected operating_point fallback row"
        )

    kafka_sensor_stream.attach_buffer(sensor_buffer)

    # === SensorStreamPoller (sensor_data_stream DB 폴링 경로) ===
    # KafkaSensorStream과의 상호배타·DB 가용성은 lifespan 진입부에서 이미 검증함.
    sensor_stream_poller: SensorStreamPoller | None = None
    if settings.sensor_stream_poll_enabled:
        assert DbContext.session_factory is not None  # 진입부 가드 통과 보장
        stream_repo = SensorStreamRepository(DbContext.session_factory)
        sensor_stream_poller = SensorStreamPoller(
            repo=stream_repo,
            sensor_buffer=sensor_buffer,
            poll_interval_sec=settings.sensor_stream_poll_interval_sec,
            fetch_limit=settings.sensor_stream_poll_batch_size,
        )

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
    app.state.sensor_stream_poller = sensor_stream_poller
    app.state.simulation_log_repo = simulation_log_repo
    app.state.realtime_engine = realtime_engine

    # === ResetService (시연용 컨테이너 재시작) ===
    # 주의: 여기서 `is_available()`로 Noop 다운그레이드를 결정하지 않는다.
    # docker-socket-proxy가 backend보다 늦게 ready되거나 일시적으로 다운된
    # 후 복구되는 케이스에서 영구 Noop으로 갇히지 않게 하기 위함. 가용성 판단은
    # 매 /api/reset 요청마다 ResetService가 adapter.is_available()를 호출해 수행한다
    # (spec §5.2.4, §11.2 startup race 항목).
    restart_adapter: ContainerRestartAdapter
    if os.getenv("RESET_BACKEND_ENABLED", "true").lower() == "true":
        try:
            restart_adapter = DockerSocketAdapter()
        except Exception as exc:
            logger.warning("docker_socket_adapter_init_failed err=%s", exc)
            restart_adapter = NoopRestartAdapter()
    else:
        restart_adapter = NoopRestartAdapter()

    reset_service = ResetService(
        restart_adapter=restart_adapter,
        backend_container=os.getenv("BACKEND_CONTAINER_NAME", "noxo-backend"),
        producer_container=os.getenv("PRODUCER_CONTAINER_NAME", "kafka-producer"),
        reset_password=os.getenv("RESET_PASSWORD") or None,
    )
    app.state.reset_service = reset_service

    await kafka_sensor_stream.start()
    if sensor_stream_poller is not None:
        await sensor_stream_poller.start()
    await realtime_engine.start()

    try:
        yield
    finally:
        await realtime_engine.stop()
        if sensor_stream_poller is not None:
            await sensor_stream_poller.stop()
        await kafka_sensor_stream.stop()
        DbContext.dispose()
