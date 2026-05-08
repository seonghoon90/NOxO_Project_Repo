"""FastAPI 의존성 주입.

singleton 컴포넌트는 app.state에 저장 (lifespan에서 초기화) → 여기서 꺼내쓴다.
테스트에서는 `app.dependency_overrides`로 임의 mock 주입 가능.
"""

from typing import Annotated

from fastapi import Depends, Request

from sqlalchemy.orm import Session

from app.adapters.forecaster import Forecaster
from app.adapters.simulator import Simulator
from app.config import Settings, get_settings
from app.core.input_injector import InputInjector
from app.core.sim_loop import SimLoopManager
from app.core.state_store import StateStore
from app.core.ws_manager import WebSocketManager
from app.db.session import get_db_session
from app.services.forecast_service import ForecastService
from app.services.sensor_service import SensorService
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


SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated["Session | None", Depends(get_db_session)]


def get_sensor_service(db: DbDep) -> SensorService:
    return SensorService(db)


def get_session_service(
    settings: SettingsDep,
    state_store: Annotated[StateStore, Depends(get_state_store)],
    injector: Annotated[InputInjector, Depends(get_input_injector)],
    sim_loop: Annotated[SimLoopManager, Depends(get_sim_loop)],
    ws_manager: Annotated[WebSocketManager, Depends(get_ws_manager)],
) -> SessionService:
    return SessionService(settings, state_store, injector, sim_loop, ws_manager)


def get_forecast_service(
    state_store: Annotated[StateStore, Depends(get_state_store)],
    forecaster: Annotated[Forecaster, Depends(get_forecaster)],
) -> ForecastService:
    return ForecastService(state_store, forecaster)


def get_threshold_service(db: DbDep) -> ThresholdService:
    return ThresholdService(db)
