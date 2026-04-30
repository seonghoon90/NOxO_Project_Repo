from datetime import datetime

from pydantic import BaseModel, Field


class StreamMessage(BaseModel):
    """WebSocket으로 push되는 시뮬 상태 메시지.

    프론트엔드 ring buffer / Trend Plot 입력 포맷.
    """

    sid: str
    t: float

    # 제어 변수 (현재값)
    syngas_flow: float
    n2_offset: float
    igv_opening: float

    # 출력 변수
    nox: float
    co: float
    flame_temp: float
    lambda_: float = Field(alias="lambda")
    power: float  # MW — IGCC.CC.G1.DWATT

    warning: bool
    ts: datetime

    model_config = {"populate_by_name": True}
