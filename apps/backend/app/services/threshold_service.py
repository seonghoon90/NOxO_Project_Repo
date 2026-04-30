"""NOx 임계치 조회. DB의 threshold_config가 있으면 그 값, 없으면 DT config 기본값."""

from sqlalchemy.orm import Session

from app.domain.threshold import Threshold
from app.repositories.threshold_repo import ThresholdRepository
from digital_twin.simulation import DEFAULT_CONFIG, DTConfig


class ThresholdService:
    def __init__(self, db: Session | None, dt_config: DTConfig = DEFAULT_CONFIG) -> None:
        self.repo = ThresholdRepository(db)
        self.dt_config = dt_config

    def get(self) -> Threshold:
        db_value = self.repo.latest_nox_limit()
        limit = db_value if db_value is not None else self.dt_config.thresholds.nox_warning_ppm
        return Threshold(nox_ppm_limit=limit)
