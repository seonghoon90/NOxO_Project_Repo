"""Forecaster Protocol — 단발 호출, 5분 horizon NOx 예측.

`DT_ARCHITECTURE.md §7-1` / `BACKEND_ARCHITECTURE.md §7` 정의.
horizon은 5분 고정, request body에는 horizon 필드 없음.

Sim Loop와 완전 분리 — 활성 세션 상태 참조 X.

ForecastInput에는 두 가지 입력 경로가 공존한다:
- features: 단발 dict — Stub용 (운영 ControlVars 10개 평탄화).
- recent_df: 1초 raw 시계열 DataFrame — ML 모델용 (SensorBuffer snapshot
  900행을 IGCC 태그명 컬럼으로 펼친 형태). digital_twin.forecaster.predict가 요구.
어느 한쪽만 채워서 호출하면 어댑터가 자신이 쓰는 필드로 분기한다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class ForecastInput:
    """예측 모델 입력."""

    features: dict[str, float] = field(default_factory=dict)
    # pd.DataFrame을 frozen dataclass에 보유하기 위해 Any로 선언 (런타임은 DataFrame).
    recent_df: Any | None = None


@dataclass(frozen=True)
class ForecastOutput:
    """예측 모델 출력 — 5분 뒤 NOx 단일 예측."""

    predicted_nox: float       # 5분 뒤 예측 NOx [ppm]
    target_time: datetime      # 현재 시각 + 5분
    threshold_exceeded: bool
    threshold_value: float


class Forecaster(Protocol):
    """현재 센서/운전 조건 → 5분 뒤 NOx 단일 예측."""

    name: str

    def predict(self, inputs: ForecastInput) -> float:
        """5분 뒤 예측 NOx [ppm]만 반환.

        threshold 비교 등 후처리는 forecast_service가 담당.
        """
        ...
