import asyncio

from app.config import Settings
from app.core.input_injector import InputInjector
from app.core.state_store import InMemoryStateStore
from app.core.ws_manager import WebSocketManager
from app.services.session_service import SessionService
from digital_twin.simulation import ControlVars


class _FakeSimLoopManager:
    def __init__(self) -> None:
        self.started: list[str] = []
        self.stopped: list[str] = []

    def start(self, sid: str) -> None:
        self.started.append(sid)

    async def stop(self, sid: str) -> None:
        self.stopped.append(sid)


class _FakeSimulationLogRepo:
    def __init__(self) -> None:
        self.session_started: list[str] = []
        self.session_finished: list[str] = []
        self.inputs: list[tuple[str, ControlVars]] = []

    def create_session_log(self, sid: str, started_at=None, notes=None) -> None:
        self.session_started.append(sid)

    def finish_session_log(self, sid: str, ended_at=None) -> None:
        self.session_finished.append(sid)

    def create_input_log(self, sid: str, controls: ControlVars, created_at=None) -> None:
        self.inputs.append((sid, controls))


def _controls() -> ControlVars:
    return ControlVars(
        syngas_flow=1500.0,
        igv_opening=75.0,
        n2_offset=200.0,
        n2_valve_1=50.0,
        syngas_srv=60.0,
        syngas_gcv_1=55.0,
        syngas_gcv_1a=55.0,
        syngas_gcv_2=55.0,
        ibh_valve=30.0,
        n2_flow=100.0,
    )


def test_start_logs_session_and_initial_input():
    repo = _FakeSimulationLogRepo()
    service = SessionService(
        settings=Settings(),
        state_store=InMemoryStateStore(),
        injector=InputInjector(),
        sim_loop=_FakeSimLoopManager(),
        ws_manager=WebSocketManager(),
        simulation_log_repo=repo,
    )

    state = service.start(_controls())

    assert repo.session_started == [state.sid]
    assert len(repo.inputs) == 1
    assert repo.inputs[0][0] == state.sid


def test_submit_control_logs_input():
    repo = _FakeSimulationLogRepo()
    service = SessionService(
        settings=Settings(),
        state_store=InMemoryStateStore(),
        injector=InputInjector(),
        sim_loop=_FakeSimLoopManager(),
        ws_manager=WebSocketManager(),
        simulation_log_repo=repo,
    )
    state = service.start()
    controls = _controls()

    service.submit_control(state.sid, controls)

    assert repo.inputs[-1] == (state.sid, controls)


def test_stop_logs_session_finish():
    repo = _FakeSimulationLogRepo()
    service = SessionService(
        settings=Settings(),
        state_store=InMemoryStateStore(),
        injector=InputInjector(),
        sim_loop=_FakeSimLoopManager(),
        ws_manager=WebSocketManager(),
        simulation_log_repo=repo,
    )
    state = service.start()

    asyncio.run(service.stop(state.sid))

    assert repo.session_finished == [state.sid]
