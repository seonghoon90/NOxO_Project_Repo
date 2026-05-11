from unittest.mock import AsyncMock, MagicMock
import pandas as pd
import pytest

from app.exceptions import DataNotEnoughError, PredictorUnavailableError
from app.services.session_service import SessionService
from digital_twin.preprocess import RAW_FEATURES


def _fake_snapshot_df(rows: int = 900) -> pd.DataFrame:
    cols = ["measured_at"] + list(RAW_FEATURES) + ["IGCC.DeNOX.AT_H1_901_PV", "IGCC.CC.G1.DWATT", "IGCC.CC.G1.TTXM"]
    return pd.DataFrame({c: [0.0] * rows if c != "measured_at"
                         else pd.date_range("2026-05-11", periods=rows, freq="1s")
                         for c in cols})


@pytest.fixture
def service():
    from app.config import Settings
    settings = Settings()
    settings.sim_max_sessions = 10
    state_store = MagicMock()
    # R-A1 (4차) — MagicMock 인스턴스의 dunder는 type lookup이라 lambda 할당으로 잡히지 않음.
    # `MagicMock(return_value=...)` 또는 `configure_mock`을 사용해야 한다.
    state_store.__len__ = MagicMock(return_value=0)
    state_store.__contains__ = MagicMock(return_value=False)
    injector = MagicMock()
    # R-A4 (4차) — ws_manager.drop_session / broadcast는 async 호출이므로 AsyncMock 필수.
    # MagicMock으로만 두면 `await ws_manager.drop_session(sid)` 시 TypeError(coroutine 미반환).
    ws_manager = MagicMock()
    ws_manager.drop_session = AsyncMock()
    ws_manager.broadcast = AsyncMock()
    sim_loop = MagicMock()
    sim_loop.stop = AsyncMock()
    from digital_twin.simulation import DEFAULT_CONFIG
    sim_loop.dt_config = DEFAULT_CONFIG
    data_source = AsyncMock()
    data_source.get_initial_snapshot.return_value = _fake_snapshot_df(900)
    simulator = MagicMock()

    from digital_twin.simulation import OutputVars
    cached_output = OutputVars(nox=25.0, exhaust_temp=580.0, power=248.6,
                               lambda_=1.1, efficiency=0.89)

    def fake_predict(controls, ctx):
        ctx.cached_output_target = cached_output
        return cached_output

    simulator.predict_for_session = MagicMock(side_effect=fake_predict)
    session_contexts: dict = {}
    svc = SessionService(
        settings=settings,
        state_store=state_store,
        injector=injector,
        sim_loop=sim_loop,
        ws_manager=ws_manager,
        data_source=data_source,
        simulator=simulator,
        session_contexts=session_contexts,
    )
    return svc, data_source, simulator, state_store, session_contexts


async def test_create_session_pulls_snapshot_from_data_source(service, monkeypatch):
    svc, data_source, simulator, _, _ = service
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    await svc.create_session("sid1")
    data_source.get_initial_snapshot.assert_called_once()


async def test_create_session_returns_503_on_data_not_enough(service, monkeypatch):
    svc, data_source, _, _, _ = service
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    data_source.get_initial_snapshot.side_effect = DataNotEnoughError("only 500")
    with pytest.raises(DataNotEnoughError):
        await svc.create_session("sid1")


async def test_create_session_calls_ml_once_on_creation(service, monkeypatch):
    svc, _, simulator, _, _ = service
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    await svc.create_session("sid1")
    assert simulator.predict_for_session.call_count == 1


async def test_create_session_retries_initial_ml_once_on_failure(service, monkeypatch):
    """U3 + §6.1 — 첫 호출 실패 → 0.5초 backoff → 두 번째 성공."""
    svc, _, simulator, _, _ = service
    sleep_mock = AsyncMock()
    monkeypatch.setattr("asyncio.sleep", sleep_mock)
    from digital_twin.simulation import OutputVars
    retry_output = OutputVars(nox=25.0, exhaust_temp=580.0, power=248.6, lambda_=1.1, efficiency=0.89)
    call_count = {"n": 0}

    def flaky_predict(controls, ctx):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("transient")
        ctx.cached_output_target = retry_output
        return retry_output

    simulator.predict_for_session.side_effect = flaky_predict
    await svc.create_session("sid1")
    sleep_mock.assert_awaited_once_with(0.5)
    assert simulator.predict_for_session.call_count == 2


async def test_create_session_returns_503_on_initial_ml_failure_production(service, monkeypatch):
    """운영 환경에서 ML 2회 모두 실패 시 PredictorUnavailableError."""
    svc, _, simulator, _, _ = service
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    simulator.predict_for_session.side_effect = RuntimeError("dead")
    with pytest.raises(PredictorUnavailableError):
        await svc.create_session("sid1")


async def test_create_session_registers_ctx_in_session_contexts(service, monkeypatch):
    """Gap 1: 성공 시 session_contexts[sid] = ctx 등록 검증."""
    svc, _, _, _, contexts = service
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    await svc.create_session("sid1")
    assert "sid1" in contexts
    # ctx는 SessionContext 인스턴스이고 cached_output_target이 채워진 상태
    from app.core.session_context import SessionContext
    assert isinstance(contexts["sid1"], SessionContext)
    assert contexts["sid1"].cached_output_target is not None


async def test_create_session_commits_state_store_and_starts_sim_loop(service, monkeypatch):
    """Gap 2: state_store.put(state) + sim_loop.start(sid) 호출 검증."""
    svc, _, _, state_store, _ = service
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    state = await svc.create_session("sid1")
    state_store.put.assert_called_once_with(state)
    svc.sim_loop.start.assert_called_once_with("sid1")


async def test_create_session_raises_session_limit_exceeded(service, monkeypatch):
    """Gap 3: state_store len이 sim_max_sessions 도달 시 SessionLimitExceededError."""
    from app.exceptions import SessionLimitExceededError
    svc, data_source, _, state_store, _ = service
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    # sim_max_sessions=10 도달 상태 시뮬레이션
    state_store.__len__ = MagicMock(return_value=10)
    with pytest.raises(SessionLimitExceededError):
        await svc.create_session("sid1")
    # I/O 전 차단 — 스냅샷 pull 호출되지 않아야 함
    data_source.get_initial_snapshot.assert_not_called()
