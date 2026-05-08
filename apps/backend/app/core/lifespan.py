"""애플리케이션 startup / shutdown 훅.

- 모든 singleton 컴포넌트(StateStore, InputInjector, WSManager, SimLoop, Predictor)를
  app.state에 attach.
- DB engine 초기화/dispose.
- shutdown 시 sim loop 전체 취소.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapters.forecaster import StubForecaster
from app.adapters.simulator import StubSimulator
from app.config import get_settings
from app.core.input_injector import InputInjector
from app.core.logging import configure_logging
from app.core.sim_loop import SimLoopManager
from app.core.state_store import InMemoryStateStore
from app.core.ws_manager import WebSocketManager
from app.db.session import DbContext


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    DbContext.init(settings.database_url)

    state_store = InMemoryStateStore()
    injector = InputInjector()
    ws_manager = WebSocketManager()
    # 두 어댑터 별도 DI 슬롯 — `BACKEND_ARCHITECTURE.md §10`
    simulator = StubSimulator()
    forecaster = StubForecaster()
    sim_loop = SimLoopManager(
        settings=settings,
        state_store=state_store,
        injector=injector,
        ws_manager=ws_manager,
        simulator=simulator,
    )

    app.state.settings = settings
    app.state.state_store = state_store
    app.state.input_injector = injector
    app.state.ws_manager = ws_manager
    app.state.simulator = simulator
    app.state.forecaster = forecaster
    app.state.sim_loop = sim_loop

    try:
        yield
    finally:
        await sim_loop.stop_all()
        DbContext.dispose()
