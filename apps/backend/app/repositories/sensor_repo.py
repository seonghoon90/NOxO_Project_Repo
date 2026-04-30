"""sensor_data 조회 repository.

DB 미연결 / 테이블 없음 상태에서는 더미 시계열로 fallback.
실제 운영에서는 DB 정의서 v1.0 sensor_data 테이블에서 SELECT.
"""

import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.sensor_data import SensorData
from app.domain.sensor import SensorReading


class SensorRepository:
    def __init__(self, db: Session | None) -> None:
        self.db = db

    def latest(self) -> SensorReading:
        if self.db is None:
            return _dummy_series(count=1)[-1]
        try:
            row = self.db.execute(
                select(SensorData).order_by(SensorData.measured_at.desc()).limit(1)
            ).scalar_one_or_none()
        except SQLAlchemyError:
            return _dummy_series(count=1)[-1]
        if row is None:
            return _dummy_series(count=1)[-1]
        return _to_domain(row)

    def history(self, limit: int = 100, offset: int = 0) -> list[SensorReading]:
        if self.db is None:
            return _dummy_series(count=limit, offset=offset)
        try:
            rows = (
                self.db.execute(
                    select(SensorData)
                    .order_by(SensorData.measured_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
                .scalars()
                .all()
            )
        except SQLAlchemyError:
            return _dummy_series(count=limit, offset=offset)
        # 시간 오름차순으로 반환 (UI에서 그래프 그리기 자연스러움)
        return [_to_domain(r) for r in reversed(rows)]


def _to_domain(row: SensorData) -> SensorReading:
    return SensorReading(
        measured_at=row.measured_at,
        nox_ppm=row.nox_ppm,
        dgan_offset=row.dgan_offset,
        syngas_flow=row.syngas_flow,
        generator_output=row.generator_output,
        npr_primary=row.npr_primary,
        ambient_temp=row.ambient_temp,
        dgan_flow=row.dgan_flow,
        igv=row.igv,
    )


def _dummy_series(count: int, offset: int = 0) -> list[SensorReading]:
    """DB 미연결 fallback. sin/cos 합성 시계열."""
    now = datetime.now(timezone.utc)
    out: list[SensorReading] = []
    total = count + offset
    for i in range(total):
        ts = now - timedelta(seconds=(total - i) * 5)
        phase = i / 30.0
        out.append(
            SensorReading(
                measured_at=ts,
                nox_ppm=25.0 + 8.0 * math.sin(phase + 0.3),
                dgan_offset=200.0 + 30.0 * math.cos(phase * 0.5),
                syngas_flow=1500.0 + 100.0 * math.sin(phase),
                generator_output=248.6 + 5.0 * math.cos(phase * 0.4),
                npr_primary=1.2 + 0.05 * math.sin(phase * 0.6),
                ambient_temp=22.0 + 2.0 * math.sin(phase * 0.2),
                dgan_flow=180.0 + 20.0 * math.cos(phase * 0.5),
                igv=75.0 + 5.0 * math.sin(phase * 0.3),
            )
        )
    return out[offset:offset + count] if offset > 0 else out
