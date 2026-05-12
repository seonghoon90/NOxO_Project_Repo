"""FastAPI 의존성 주입.

singleton 컴포넌트는 app.state에 저장 (lifespan에서 초기화) → 여기서 꺼내쓴다.
테스트에서는 `app.dependency_overrides`로 임의 mock 주입 가능.
"""

from typing import Annotated

from fastapi import Depends, Request

from app.adapters.data_source import PlantDataSource
from app.adapters.forecaster import Forecaster
from app.adapters.simulator import Simulator
from app.config import Settings, get_settings
from app.core.input_injector import InputInjector
from app.core.kafka_stream import KafkaSensorStream
from app.core.sim_loop import SimLoopManager
from app.core.state_store import StateStore
from app.core.ws_manager import WebSocketManager
from app.repositories.simulation_log_repo import SimulationLogRepository
from app.services.forecast_service import ForecastService
from app.services.session_service import SessionService
from app.services.threshold_service import ThresholdService


def get_state_store(request: Request) -> StateStore:
    return request.app.state.state_store


def get_input_injector(request: Request) -> InputInjector:
    return request.app.state.input_injector


def get_ws_manager(request: Request) -> WebSocketManager:
    return request.app.state.ws_manager


def get_sim_loop(request: Request) -> SimLoopManager:
    return request.app.state.sim_loop


def get_simulator(request: Request) -> Simulator:
    return request.app.state.simulator


def get_forecaster(request: Request) -> Forecaster:
    return request.app.state.forecaster


def get_kafka_sensor_stream(request: Request) -> KafkaSensorStream:
    return request.app.state.kafka_sensor_stream


def get_simulation_log_repo(request: Request) -> SimulationLogRepository | None:
    return getattr(request.app.state, "simulation_log_repo", None)


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_data_source(request: Request) -> PlantDataSource | None:
    return getattr(request.app.state, "data_source", None)


def get_session_contexts(request: Request) -> dict:
    return request.app.state.session_contexts


def get_session_service(
    settings: SettingsDep,
    state_store: Annotated[StateStore, Depends(get_state_store)],
    injector: Annotated[InputInjector, Depends(get_input_injector)],
    sim_loop: Annotated[SimLoopManager, Depends(get_sim_loop)],
    ws_manager: Annotated[WebSocketManager, Depends(get_ws_manager)],
    data_source: Annotated[PlantDataSource | None, Depends(get_data_source)],
    simulator: Annotated[Simulator, Depends(get_simulator)],
    session_contexts: Annotated[dict, Depends(get_session_contexts)],
    simulation_log_repo: Annotated[
        SimulationLogRepository | None, Depends(get_simulation_log_repo)
    ],
) -> SessionService:
    return SessionService(
        settings, state_store, injector, sim_loop, ws_manager,
        data_source=data_source,
        simulator=simulator,
        session_contexts=session_contexts,
        simulation_log_repo=simulation_log_repo,
    )


def get_forecast_service(
    state_store: Annotated[StateStore, Depends(get_state_store)],
    forecaster: Annotated[Forecaster, Depends(get_forecaster)],
    simulation_log_repo: Annotated[
        SimulationLogRepository | None, Depends(get_simulation_log_repo)
    ],
) -> ForecastService:
    return ForecastService(
        state_store,
        forecaster,
        simulation_log_repo=simulation_log_repo,
    )


def get_threshold_service() -> ThresholdService:
    return ThresholdService()
