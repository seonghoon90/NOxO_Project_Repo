"""5분 horizon NOx 예측 모델 (기존 시뮬레이션 모델과 독립).

설계 문서: docs/superpowers/specs/2026-05-12-forecaster-5min-nox-design.md
"""

from digital_twin.forecaster.predict import LoadedForecaster, load_model, predict

__all__ = ["LoadedForecaster", "load_model", "predict"]
