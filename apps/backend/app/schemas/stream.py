"""WebSocket 실시간 스트림 payload schema (envelope v1).

spec: docs/superpowers/specs/2026-05-12-realtime-prediction-design.md §2.2
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StreamControls(BaseModel):
    """제어 10개 변수 (도메인 snake_case)."""
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


class StreamOutputs(BaseModel):
    """DT current 추론 결과 5개.

    단위: nox(ppm), exhaust_temp(°C), power(MW), lambda_(무차원), efficiency([0,1])
    """
    model_config = ConfigDict(populate_by_name=True)

    nox: float
    exhaust_temp: float
    power: float
    lambda_: float = Field(alias="lambda_")
    efficiency: float


class StreamCurrent(BaseModel):
    controls: StreamControls
    outputs: StreamOutputs


class StreamKafkaLatest(BaseModel):
    controls: StreamControls
    ts: datetime


class StreamForecast(BaseModel):
    predicted_nox: float
    target_time: datetime
    threshold_value: float
    threshold_exceeded: bool


class RealtimeStreamPayload(BaseModel):
    """WS /api/session/{sid}/stream 메시지 envelope.

    spec §2.2. v=1 고정. mode/override 조합별 필드 채움 규칙은 spec 참조.
    """

    v: Literal[1] = 1
    sid: str
    tick: int
    ts: datetime
    mode: Literal["sim", "realtime"]
    override_active: bool
    current: StreamCurrent
    kafka_latest: StreamKafkaLatest | None = None
    forecast: StreamForecast | None = None
    warning: str | None = None


# 임시 호환 stub — Task 9에서 sim_loop.py / endpoints/stream.py 사용처 제거 후 삭제.
StreamMessage = RealtimeStreamPayload  # noqa: F841
