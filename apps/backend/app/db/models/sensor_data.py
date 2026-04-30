"""sensor_data 테이블 ORM 모델.

DB 정의서(database/db_definition.md v1.1) 기준 9개 컬럼.
"""

from datetime import datetime

from sqlalchemy import Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SensorData(Base):
    __tablename__ = "sensor_data"

    measured_at: Mapped[datetime] = mapped_column(primary_key=True)
    nox_ppm: Mapped[float | None] = mapped_column(Float)
    dgan_offset: Mapped[float | None] = mapped_column(Float)
    syngas_flow: Mapped[float | None] = mapped_column(Float)
    generator_output: Mapped[float | None] = mapped_column(Float)
    npr_primary: Mapped[float | None] = mapped_column(Float)
    ambient_temp: Mapped[float | None] = mapped_column(Float)
    dgan_flow: Mapped[float | None] = mapped_column(Float)
    igv: Mapped[float | None] = mapped_column(Float)

    __table_args__ = ({"comment": "DCS 센서 1초 단위 측정 데이터"},)

    def __repr__(self) -> str:
        return f"<SensorData ts={self.measured_at} nox={self.nox_ppm}>"
