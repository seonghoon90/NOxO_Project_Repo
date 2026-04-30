"""threshold_config 테이블 ORM 모델 (스텁).

DB 팀 임계값 정의 보류 상태 — 가안 컬럼으로 미리 정의해 두고,
테이블이 실제로 존재할 때만 SELECT를 시도한다 (없으면 config 하드코딩 fallback).

협의 후 컬럼 명세가 확정되면 본 파일과 ThresholdRepository 일치시킨다.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ThresholdConfig(Base):
    __tablename__ = "threshold_config"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    metric: Mapped[str] = mapped_column(String(32))           # 'nox_ppm' 등
    limit_value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16))             # 'ppm' 등
    effective_from: Mapped[datetime] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()   # NULL이면 현재 적용 중
    source: Mapped[str | None] = mapped_column(String(255))   # 출처 — [조사 필요]

    __table_args__ = ({"comment": "운영 임계값 (가안 — DB팀 협의 후 확정)"},)
