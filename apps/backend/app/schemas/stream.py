from datetime import datetime

from pydantic import BaseModel, Field


class StreamMessage(BaseModel):
    """WebSocket으로 push되는 시뮬 상태 메시지.

    프론트엔드 ring buffer / Trend Plot 입력 포맷.
    `DT_ARCHITECTURE.md §10` — 평면 구조 (제어 10 + 출력 + meta).
    `co`는 학습 타겟에서 제외, `efficiency`는 백엔드 sim_loop 후처리.
    """

    sid: str
    t: float

    # 제어 변수 (현재값) — 10개
    syngas_flow: float
    igv_opening: float
    n2_offset: float
    n2_valve_1: float
    syngas_srv: float
    syngas_gcv_1: float
    syngas_gcv_1a: float
    syngas_gcv_2: float
    ibh_valve: float
    n2_flow: float

    # 출력 변수 — `co` 제외, `efficiency` 추가 (백엔드 후처리값)
    nox: float
    exhaust_temp: float
    lambda_: float = Field(alias="lambda")
    power: float  # MW — IGCC.CC.G1.DWATT
    efficiency: float

    warning: bool
    ts: datetime

    model_config = {"populate_by_name": True}
