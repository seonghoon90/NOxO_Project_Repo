"""FastAPI 의존성 주입.

singleton 컴포넌트는 app.state에 저장 (lifespan에서 초기화) → 여기서 꺼내쓴다.
테스트에서는 `app.dependency_overrides`로 임의 mock 주입 가능.
"""

from typing import Annotated

from fastapi import Depends, Request

from app.adapters.forecaster import Forecaster
from app.adapters.simulator import Simulator
from app.config import Settings, get_settings
from app.core.kafka_stream import KafkaSensorStream
from app.core.sensor_buffer import SensorBuffer
from app.core.session import Session
from app.core.ws_manager import WebSocketManager
from app.repositories.simulation_log_repo import SimulationLogRepository
from app.services.forecast_service import ForecastService
from app.services.session_service import SessionService
from app.services.threshold_service import ThresholdService


def get_ws_manager(request: Request) -> WebSocketManager:
    return request.app.state.ws_manager


def get_simulator(request: Request) -> Simulator:
    return request.app.state.simulator


def get_forecaster(request: Request) -> Forecaster:
    return request.app.state.forecaster


def get_kafka_sensor_stream(request: Request) -> KafkaSensorStream:
    return request.app.state.kafka_sensor_stream


def get_simulation_log_repo(request: Request) -> SimulationLogRepository | None:
    return getattr(request.app.state, "simulation_log_repo", None)


def get_sensor_buffer(request: Request) -> SensorBuffer:
    return request.app.state.sensor_buffer


def get_sessions(request: Request) -> dict[str, Session]:
    return request.app.state.sessions


def get_realtime_engine(request: Request):
    return request.app.state.realtime_engine


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_session_service(
    settings: SettingsDep,
    sessions: Annotated[dict, Depends(get_sessions)],
    sensor_buffer: Annotated[SensorBuffer, Depends(get_sensor_buffer)],
    ws_manager: Annotated[WebSocketManager, Depends(get_ws_manager)],
    simulation_log_repo: Annotated[
        SimulationLogRepository | None, Depends(get_simulation_log_repo)
    ],
) -> SessionService:
    return SessionService(
        settings=settings,
        sessions=sessions,
        sensor_buffer=sensor_buffer,
        ws_manager=ws_manager,
        simulation_log_repo=simulation_log_repo,
    )


def get_forecast_service(
    sessions: Annotated[dict, Depends(get_sessions)],
    forecaster: Annotated[Forecaster, Depends(get_forecaster)],
    simulation_log_repo: Annotated[
        SimulationLogRepository | None, Depends(get_simulation_log_repo)
    ],
) -> ForecastService:
    return ForecastService(
        sessions,
        forecaster,
        simulation_log_repo=simulation_log_repo,
    )


def get_threshold_service() -> ThresholdService:
    return ThresholdService()
