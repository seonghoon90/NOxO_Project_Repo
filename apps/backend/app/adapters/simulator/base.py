"""Simulator Protocol — Sim Loop가 매 step 호출하는 정상상태 회귀 모델.

`DT_ARCHITECTURE.md §7-1` 정의에 따라 ControlVars(10개) → OutputVars로 매 step 추론.
Forecaster와 별도 슬롯으로 운영된다 (`BACKEND_ARCHITECTURE.md §10`).
"""

from typing import Protocol

from digital_twin.simulation import ControlVars, OutputVars


class Simulator(Protocol):
    """제어 입력 → 정상상태 출력 추정. 매 sim step 호출."""

    name: str

    def predict(self, controls: ControlVars) -> OutputVars: ...
