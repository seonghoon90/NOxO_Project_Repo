from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 전역 설정 — 환경변수 또는 .env에서 주입."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 앱
    app_name: str = "NOxO Backend"
    app_version: str = "0.1.0"
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    # DB (Phase 1: 연결만 준비, 실제 쿼리는 inmemory repository)
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    sensor_column_mapping: dict[str, str] | None = Field(
        default=None,
        alias="SENSOR_COLUMN_MAPPING",
    )

    # 시뮬 루프 — 백엔드 전용 설정 (세션 수 제한)
    # τ / dt / 임계치는 digital_twin.simulation.DEFAULT_CONFIG가 단일 진실원.
    sim_max_sessions: int = 10

    # 합성가스 LHV (Lower Heating Value) — efficiency 후처리에 사용.
    # `BACKEND_PRD.md §11` / `DT_ARCHITECTURE.md §10` — `[조사 필요]` 단위 환산.
    # 가안: 합성가스 LHV ≈ 11 MJ/Nm³. 실측 평균값 확보 후 재산정 필요.
    syngas_lhv: float = 11.0

    # Kafka-compatible streaming simulation
    kafka_stream_enabled: bool = Field(default=False, alias="KAFKA_STREAM_ENABLED")
    kafka_bootstrap_servers: str = Field(
        default="localhost:19092",
        alias="KAFKA_BOOTSTRAP_SERVERS",
    )
    kafka_sensor_topic: str = Field(default="noxo.sensor.raw", alias="KAFKA_SENSOR_TOPIC")
    kafka_consumer_group_id: str = Field(
        default="noxo-backend-stream",
        alias="KAFKA_CONSUMER_GROUP_ID",
    )
    kafka_bootstrap_minutes: int = Field(default=15, alias="KAFKA_BOOTSTRAP_MINUTES")
    kafka_bootstrap_file: str | None = Field(
        default=None,
        alias="KAFKA_BOOTSTRAP_FILE",
    )

    # sensor_data_stream DB polling (KafkaSensorStream 대안 경로)
    # KAFKA_STREAM_ENABLED와 상호배타 — lifespan에서 검증한다.
    sensor_stream_poll_enabled: bool = Field(
        default=False,
        alias="SENSOR_STREAM_POLL_ENABLED",
    )
    sensor_stream_poll_interval_sec: float = Field(
        default=1.0,
        alias="SENSOR_STREAM_POLL_INTERVAL_SEC",
    )
    sensor_stream_poll_batch_size: int = Field(
        default=200,
        alias="SENSOR_STREAM_POLL_BATCH_SIZE",
    )

    # CORS (개발 시 별도 호스트에서 접근 허용)
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
