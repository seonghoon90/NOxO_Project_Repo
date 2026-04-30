from datetime import datetime

from pydantic import BaseModel


class SensorPayload(BaseModel):
    """DB 정의서 §1 컬럼명을 그대로 노출."""

    measured_at: datetime
    nox_ppm: float | None = None
    dgan_offset: float | None = None
    syngas_flow: float | None = None
    generator_output: float | None = None
    npr_primary: float | None = None
    ambient_temp: float | None = None
    dgan_flow: float | None = None
    igv: float | None = None


class SensorHistoryQuery(BaseModel):
    start: datetime | None = None
    end: datetime | None = None
    limit: int = 100
    offset: int = 0
