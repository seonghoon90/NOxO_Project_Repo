"""NOx 임계치 조회. DB의 threshold_config가 있으면 그 값, 없으면 config 하드코딩."""

from sqlalchemy.orm import Session

from app.config import Settings
from app.domain.threshold import Threshold
from app.repositories.threshold_repo import ThresholdRepository


class ThresholdService:
    def __init__(self, settings: Settings, db: Session | None) -> None:
        self.settings = settings
        self.repo = ThresholdRepository(db)

    def get(self) -> Threshold:
        db_value = self.repo.latest_nox_limit()
        limit = db_value if db_value is not None else self.settings.nox_threshold_ppm
        return Threshold(nox_ppm_limit=limit)
