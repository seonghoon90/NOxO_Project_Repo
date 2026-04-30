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

    # 시뮬 루프
    sim_dt_seconds: float = 0.2  # WebSocket push 주기 (200ms)
    sim_max_sessions: int = 10

    # 시간 상수 τ (단위: 초) — [조사 필요] 실측 도출
    tau_fuel: float = 1.0
    tau_n2: float = 1.0
    tau_igv: float = 2.0
    tau_temp: float = 10.0
    tau_nox: float = 5.0
    tau_co: float = 3.0
    tau_power: float = 8.5

    # 임계치 — [조사 필요]
    nox_threshold_ppm: float = 50.0

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
