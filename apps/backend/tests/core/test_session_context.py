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


def test_from_snapshot_builds_buffer_with_40_columns():
    """스냅샷 43컬럼 → buffer 행 40 키 (measured_at, NOx, DWATT drop, TTXM 유지)."""
    from digital_twin.preprocess import RAW_FEATURES
    cols = ["measured_at"] + list(RAW_FEATURES) + ["IGCC.DeNOX.AT_H1_901_PV", "IGCC.CC.G1.DWATT", "IGCC.CC.G1.TTXM"]
    df = pd.DataFrame({c: [0.0] * 900 if c != "measured_at"
                       else pd.date_range("2026-05-11", periods=900, freq="1s")
                       for c in cols})
    ctx = SessionContext.from_snapshot("sid1", df)
    first_row = ctx.recent_df_buffer[0]
    assert len(first_row) == 40
    assert "measured_at" not in first_row
    assert "IGCC.DeNOX.AT_H1_901_PV" not in first_row
    assert "IGCC.CC.G1.DWATT" not in first_row
    assert "IGCC.CC.G1.TTXM" in first_row


def test_from_snapshot_extracts_plant_context_30_keys():
    """plant_context = RAW 39 - CONTROL_TAGS 10 + TTXM 1 = 30 키."""
    from digital_twin.preprocess import RAW_FEATURES
    cols = ["measured_at"] + list(RAW_FEATURES) + ["IGCC.DeNOX.AT_H1_901_PV", "IGCC.CC.G1.DWATT", "IGCC.CC.G1.TTXM"]
    df = pd.DataFrame({c: [0.0] * 900 if c != "measured_at"
                       else pd.date_range("2026-05-11", periods=900, freq="1s")
                       for c in cols})
    ctx = SessionContext.from_snapshot("sid2", df)
    assert len(ctx.plant_context) == 30
    assert "IGCC.CC.G1.TTXM" in ctx.plant_context


def test_from_snapshot_extracts_initial_controls_10_keys():
    """initial_controls = CONTROL_TAGS 10 키, 스냅샷 마지막 행 값."""
    from app.domain.tags import CONTROL_TAGS
    from digital_twin.preprocess import RAW_FEATURES
    cols = ["measured_at"] + list(RAW_FEATURES) + ["IGCC.DeNOX.AT_H1_901_PV", "IGCC.CC.G1.DWATT", "IGCC.CC.G1.TTXM"]
    df = pd.DataFrame({c: [42.0] * 900 if c != "measured_at"
                       else pd.date_range("2026-05-11", periods=900, freq="1s")
                       for c in cols})
    ctx = SessionContext.from_snapshot("sid3", df)
    assert len(ctx.initial_controls) == 10
    for tag in CONTROL_TAGS:
        assert ctx.initial_controls[tag] == 42.0


def test_from_snapshot_buffer_length_matches_snapshot():
    """입력 900행 → deque 길이 900."""
    from digital_twin.preprocess import RAW_FEATURES
    cols = ["measured_at"] + list(RAW_FEATURES) + ["IGCC.DeNOX.AT_H1_901_PV", "IGCC.CC.G1.DWATT", "IGCC.CC.G1.TTXM"]
    df = pd.DataFrame({c: [0.0] * 900 if c != "measured_at"
                       else pd.date_range("2026-05-11", periods=900, freq="1s")
                       for c in cols})
    ctx = SessionContext.from_snapshot("sid4", df)
    assert len(ctx.recent_df_buffer) == 900


def test_from_snapshot_plant_context_disjoint_from_controls():
    """plant_context ∩ CONTROL_TAGS = ∅ (NS7 invariant)."""
    from app.domain.tags import CONTROL_TAGS
    from digital_twin.preprocess import RAW_FEATURES
    cols = ["measured_at"] + list(RAW_FEATURES) + ["IGCC.DeNOX.AT_H1_901_PV", "IGCC.CC.G1.DWATT", "IGCC.CC.G1.TTXM"]
    df = pd.DataFrame({c: [0.0] * 900 if c != "measured_at"
                       else pd.date_range("2026-05-11", periods=900, freq="1s")
                       for c in cols})
    ctx = SessionContext.from_snapshot("sid5", df)
    for tag in CONTROL_TAGS:
        assert tag not in ctx.plant_context
