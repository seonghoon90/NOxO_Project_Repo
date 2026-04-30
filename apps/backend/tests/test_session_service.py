import asyncio

from app.config import Settings
from app.core.input_injector import InputInjector
from app.core.state_store import InMemoryStateStore
from app.domain.tags import ControlVars
from app.services.session_service import SessionService


class _FakeSimLoopManager:
    def __init__(self) -> None:
        self.stopped: list[str] = []

    async def stop(self, sid: str) -> None:
        self.stopped.append(sid)


class _FakeWebSocketManager:
    def __init__(self) -> None:
        self.dropped: list[str] = []

    async def drop_session(self, sid: str) -> None:
        self.dropped.append(sid)


def test_stop_missing_sid_still_runs_best_effort_cleanup():
    sid = "orphan-sid"
    state_store = InMemoryStateStore()
    injector = InputInjector()
    injector.submit(
        sid,
        ControlVars(syngas_flow=1500.0, n2_offset=200.0, igv_opening=75.0),
    )
    sim_loop = _FakeSimLoopManager()
    ws_manager = _FakeWebSocketManager()
    service = SessionService(
        settings=Settings(),
        state_store=state_store,
        injector=injector,
        sim_loop=sim_loop,
        ws_manager=ws_manager,
    )

    asyncio.run(service.stop(sid))

    assert sim_loop.stopped == [sid]
    assert ws_manager.dropped == [sid]
    assert injector.consume(sid) is None
