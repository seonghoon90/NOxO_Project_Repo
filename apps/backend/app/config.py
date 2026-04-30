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

    # 시뮬 루프 — 백엔드 전용 설정 (세션 수 제한)
    # τ / dt / 임계치는 digital_twin.simulation.DEFAULT_CONFIG가 단일 진실원.
    sim_max_sessions: int = 10

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
