from collections import deque
import pandas as pd
import pytest

from app.core.session_context import SessionContext


@pytest.fixture
def plant_context_sample():
    """30 키 sample (외란 29 + TTXM 1) — 실제 RAW_FEATURES 외란명 사용."""
    from digital_twin.preprocess import RAW_FEATURES
    from app.domain.tags import CONTROL_TAGS
    disturbance = [c for c in RAW_FEATURES if c not in CONTROL_TAGS]
    pc = {k: 1.0 for k in disturbance}
    pc["IGCC.CC.G1.TTXM"] = 580.0
    return pc


@pytest.fixture
def ctx_basic(plant_context_sample):
    """단순 buffer 비어있는 SessionContext."""
    return SessionContext(
        sid="test",
        plant_context=plant_context_sample,
        recent_df_buffer=deque(maxlen=900),
        initial_controls={k: 0.0 for k in __import__("app.domain.tags", fromlist=["CONTROL_TAGS"]).CONTROL_TAGS},
    )


def test_push_step_row_freezes_disturbances(ctx_basic):
    """매 push 시 외란 키 값은 plant_context 그대로 유지."""
    from app.domain.tags import CONTROL_TAGS
    controls = {tag: 999.0 for tag in CONTROL_TAGS}
    ctx_basic.push_step_row(controls)
    row = ctx_basic.recent_df_buffer[-1]
    for k, v in ctx_basic.plant_context.items():
        assert row[k] == v


def test_push_step_row_updates_controls(ctx_basic):
    """제어 10개만 controls 값으로 갱신."""
    from app.domain.tags import CONTROL_TAGS
    controls = {tag: 42.0 for tag in CONTROL_TAGS}
    ctx_basic.push_step_row(controls)
    row = ctx_basic.recent_df_buffer[-1]
    for tag in CONTROL_TAGS:
        assert row[tag] == 42.0


def test_push_step_row_controls_override_plant_context(ctx_basic):
    """plant_context와 controls가 겹쳐도 controls가 우선 (방어적)."""
    ctx_basic.plant_context["IGCC.CC.G1.ca_fqsg_cl"] = 100.0  # CONTROL 키와 충돌
    ctx_basic.push_step_row({"IGCC.CC.G1.ca_fqsg_cl": 200.0})
    row = ctx_basic.recent_df_buffer[-1]
    assert row["IGCC.CC.G1.ca_fqsg_cl"] == 200.0


def test_buffer_maxlen_900_evicts_oldest(ctx_basic):
    """901번째 push 시 가장 오래된 행 자동 drop."""
    from app.domain.tags import CONTROL_TAGS
    for i in range(901):
        ctx_basic.push_step_row({tag: float(i) for tag in CONTROL_TAGS})
    assert len(ctx_basic.recent_df_buffer) == 900
    # 가장 오래된 행이 빠졌으므로 첫 행의 control 값은 1.0
    assert ctx_basic.recent_df_buffer[0][CONTROL_TAGS[0]] == 1.0


def test_buffer_to_df_preserves_insertion_order(ctx_basic):
    """오래된 → 최신 순서 유지."""
    from app.domain.tags import CONTROL_TAGS
    for i in range(5):
        ctx_basic.push_step_row({tag: float(i) for tag in CONTROL_TAGS})
    df = ctx_basic.buffer_to_df()
    assert list(df[CONTROL_TAGS[0]]) == [0.0, 1.0, 2.0, 3.0, 4.0]


def test_buffer_to_df_returns_dataframe(ctx_basic):
    """buffer_to_df는 pandas DataFrame 반환."""
    from app.domain.tags import CONTROL_TAGS
    ctx_basic.push_step_row({tag: 0.0 for tag in CONTROL_TAGS})
    df = ctx_basic.buffer_to_df()
    assert isinstance(df, pd.DataFrame)
