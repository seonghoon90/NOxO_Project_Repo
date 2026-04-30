from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.tags import (
    TAG_IGV_OPENING,
    TAG_N2_OFFSET,
    TAG_SYNGAS_FLOW,
    ControlVars,
)


class ControlPayload(BaseModel):
    """프론트엔드 ▲▼ 조작 결과로 전달되는 제어 변수 묶음.

    JSON 키는 실제 태그 식별자 그대로 사용한다.
    예) {"IGCC.CC.G1.ca_fqsg_cl": 1500, ...}
    """

    syngas_flow: float = Field(alias=TAG_SYNGAS_FLOW)
    n2_offset: float = Field(alias=TAG_N2_OFFSET)
    igv_opening: float = Field(alias=TAG_IGV_OPENING)

    model_config = {"populate_by_name": True}

    def to_domain(self) -> ControlVars:
        return ControlVars(
            syngas_flow=self.syngas_flow,
            n2_offset=self.n2_offset,
            igv_opening=self.igv_opening,
        )


class StartSessionRequest(BaseModel):
    initial_condition: ControlPayload | None = None


class OutputPayload(BaseModel):
    nox: float
    co: float
    flame_temp: float
    lambda_: float = Field(alias="lambda")
    power: float

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
