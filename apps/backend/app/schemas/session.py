from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.tags import (
    TAG_IBH_VALVE,
    TAG_IGV_OPENING,
    TAG_N2_FLOW,
    TAG_N2_OFFSET,
    TAG_N2_VALVE_1,
    TAG_SYNGAS_FLOW,
    TAG_SYNGAS_GCV_1,
    TAG_SYNGAS_GCV_1A,
    TAG_SYNGAS_GCV_2,
    TAG_SYNGAS_SRV,
)
from digital_twin.simulation import ControlVars


class ControlPayload(BaseModel):
    """프론트엔드 ▲▼ 조작 결과로 전달되는 제어 변수 묶음 (10개).

    JSON 키는 실제 태그 식별자 그대로 사용한다.
    예) {"IGCC.CC.G1.ca_fqsg_cl": 1500, "IGCC.CC.G1.csgv": 75, ...}
    """

    syngas_flow: float = Field(alias=TAG_SYNGAS_FLOW)
    igv_opening: float = Field(alias=TAG_IGV_OPENING)
    n2_offset: float = Field(alias=TAG_N2_OFFSET)
    n2_valve_1: float = Field(alias=TAG_N2_VALVE_1)
    syngas_srv: float = Field(alias=TAG_SYNGAS_SRV)
    syngas_gcv_1: float = Field(alias=TAG_SYNGAS_GCV_1)
    syngas_gcv_1a: float = Field(alias=TAG_SYNGAS_GCV_1A)
    syngas_gcv_2: float = Field(alias=TAG_SYNGAS_GCV_2)
    ibh_valve: float = Field(alias=TAG_IBH_VALVE)
    n2_flow: float = Field(alias=TAG_N2_FLOW)

    model_config = {"populate_by_name": True}

    def to_domain(self) -> ControlVars:
        return ControlVars(
            syngas_flow=self.syngas_flow,
            igv_opening=self.igv_opening,
            n2_offset=self.n2_offset,
            n2_valve_1=self.n2_valve_1,
            syngas_srv=self.syngas_srv,
            syngas_gcv_1=self.syngas_gcv_1,
            syngas_gcv_1a=self.syngas_gcv_1a,
            syngas_gcv_2=self.syngas_gcv_2,
            ibh_valve=self.ibh_valve,
            n2_flow=self.n2_flow,
        )


class StartSessionRequest(BaseModel):
    initial_condition: ControlPayload | None = None


class OutputPayload(BaseModel):
    """SnapshotResponse의 출력 변수 묶음.

    `co`는 학습 타겟에서 제외, `efficiency`는 백엔드 sim_loop 후처리값.
    """

    nox: float
    exhaust_temp: float
    lambda_: float = Field(alias="lambda")
    power: float
    efficiency: float

    model_config = {"populate_by_name": True}


class SnapshotResponse(BaseModel):
    sid: str
    t: float
    target: ControlPayload
    current: ControlPayload
    output: OutputPayload
    warning: bool
    last_updated: datetime


class StartSessionResponse(BaseModel):
    sid: str
    snapshot: SnapshotResponse
