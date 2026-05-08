"""Forecaster Protocol — 단발 호출, 5분 horizon NOx 예측.

`DT_ARCHITECTURE.md §7-1` / `BACKEND_ARCHITECTURE.md §7` 정의.
horizon은 5분 고정, request body에는 horizon 필드 없음.
입력 피처 구성은 `[추후 결정]` (피처 엔지니어링 후 확정).

Sim Loop와 완전 분리 — 활성 세션 상태 참조 X.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ForecastInput:
    """예측 모델 입력 — 현재 센서값 + 운전 조건.

    `features` dict의 키 구성은 [추후 결정].
    후보: 제어 10개 + 외란/파생 변수 일부 (피처 엔지니어링 결과 따름).
    """

    features: dict[str, float]


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
