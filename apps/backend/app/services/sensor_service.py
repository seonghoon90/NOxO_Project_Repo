"""센서 데이터 조회 서비스.

DB가 연결되어 있으면 sensor_data 테이블에서 조회, 아니면 repository가 더미로 fallback.
"""

from sqlalchemy.orm import Session

from app.domain.sensor import SensorReading
from app.repositories.sensor_repo import SensorRepository


class SensorService:
    def __init__(self, db: Session | None) -> None:
        self.repo = SensorRepository(db)

    def latest(self) -> SensorReading:
        return self.repo.latest()

    def history(self, limit: int = 100, offset: int = 0) -> list[SensorReading]:
        return self.repo.history(limit=limit, offset=offset)
