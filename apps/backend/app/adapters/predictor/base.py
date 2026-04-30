from typing import Protocol

from app.domain.tags import ControlVars, OutputVars


class Predictor(Protocol):
    """제어 입력 → 정상상태 출력 추정. 실제 ML 모델 도입 시 본 인터페이스만 구현."""

    name: str

    def predict(self, controls: ControlVars) -> OutputVars: ...
