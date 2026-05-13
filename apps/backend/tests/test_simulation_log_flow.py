"""SessionService → simulation_log_repo 호출 흐름 검증.

spec §3.5: 세션 시작 시 initial input_log는 더 이상 적재하지 않는다
(모든 세션이 동일 운전점에서 시작 → 의미 없음). submit_control 호출 시만 적재.
"""

import asyncio
from unittest.mock import AsyncMock

from app.config import Settings
from app.core.sensor_buffer import SensorBuffer
from app.services.session_service import SessionService
from digital_twin.simulation import ControlVars


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
        syngas_flow=1500.0, igv_opening=75.0, n2_offset=200.0, n2_valve_1=50.0,
        syngas_srv=60.0, syngas_gcv_1=55.0, syngas_gcv_1a=55.0, syngas_gcv_2=55.0,
        ibh_valve=30.0, n2_flow=100.0,
    )


def _make_buffer() -> SensorBuffer:
    buf = SensorBuffer(maxlen=900)
    buf.load_bootstrap([
        {
            "syngas_flow": 1500.0, "igv_opening": 75.0,
            "n2_offset": 200.0, "n2_valve_1": 50.0,
            "syngas_srv": 60.0, "syngas_gcv_1": 55.0,
            "syngas_gcv_1a": 55.0, "syngas_gcv_2": 55.0,
            "ibh_valve": 30.0, "n2_flow": 100.0,
        }
    ])
    return buf


def _make_service(repo: _FakeSimulationLogRepo) -> SessionService:
    return SessionService(
        settings=Settings(),
        sessions={},
        sensor_buffer=_make_buffer(),
        ws_manager=AsyncMock(),
        simulation_log_repo=repo,
    )


def test_start_logs_session_only_not_initial_input():
    repo = _FakeSimulationLogRepo()
    service = _make_service(repo)

    session = service.start()

    assert repo.session_started == [session.sid]
    assert repo.inputs == []  # 초기 input은 적재하지 않음 (spec §3.5)


def test_submit_control_logs_input():
    repo = _FakeSimulationLogRepo()
    service = _make_service(repo)
    session = service.start()
    controls = _controls()

    service.submit_control(session.sid, controls)

    assert repo.inputs[-1] == (session.sid, controls)


def test_stop_logs_session_finish():
    repo = _FakeSimulationLogRepo()
    service = _make_service(repo)
    session = service.start()

    asyncio.run(service.stop(session.sid))

    assert repo.session_finished == [session.sid]
