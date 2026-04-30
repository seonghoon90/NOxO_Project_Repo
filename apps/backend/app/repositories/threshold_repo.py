"""threshold_config 조회 repository (스텁).

테이블 미정의 상태이므로 SELECT 시도 → 실패 시 None 반환.
ThresholdService가 None일 때 config 하드코딩 fallback 처리.
"""

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.threshold_config import ThresholdConfig


class ThresholdRepository:
    def __init__(self, db: Session | None) -> None:
        self.db = db

    def latest_nox_limit(self) -> float | None:
        """nox_ppm 임계치의 현재 적용값. 없거나 DB 미연결이면 None."""
        if self.db is None:
            return None
        try:
            row = self.db.execute(
                select(ThresholdConfig)
                .where(ThresholdConfig.metric == "nox_ppm")
                .where(ThresholdConfig.effective_to.is_(None))
                .order_by(ThresholdConfig.effective_from.desc())
                .limit(1)
            ).scalar_one_or_none()
        except SQLAlchemyError:
            # 테이블 자체가 없거나 컬럼 mismatch면 fallback
            return None
        return row.limit_value if row is not None else None
