"""센서 측정값 도메인 모델.

DB 정의서(database/db_definition.md v1.1) 컬럼과 1:1 매핑.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SensorReading:
    measured_at: datetime
    nox_ppm: float | None
    dgan_offset: float | None
    syngas_flow: float | None
    generator_output: float | None
    npr_primary: float | None
    ambient_temp: float | None
    dgan_flow: float | None
    igv: float | None
