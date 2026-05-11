"""ML 기반 Simulator — Ridge·LGB 앙상블.

Simulator Protocol(외부): predict(controls) — NotImplementedError. SimLoopManager가 클로저로 ctx 바인딩.
실제 추론 본체: predict_for_session(controls, session_ctx).
"""

import time
import warnings
from pathlib import Path

from digital_twin.simulation import ControlVars, OutputVars
from app.core.session_context import SessionContext
from app.exceptions import PredictorUnavailableError, SessionTerminatedError

ML_INTERVAL_SEC = 60.0
DEBOUNCE_SEC = 1.0
ML_MAX_FAILURES = 5


class MLSimulator:
    name = "ml"

    def __init__(self, models_dir: Path | None = None):
        """models_dir이 None이면 production 기본 경로 사용."""
        from digital_twin.predict import load_models, MODELS_DIR
        target_dir = models_dir or MODELS_DIR
        try:
            self.lgb, self.ridge = load_models(
                lgb_path=str(target_dir / "dt_lgb_model.pkl"),
                ridge_path=str(target_dir / "dt_ridge_model.pkl"),
            )
        except FileNotFoundError as e:
            raise PredictorUnavailableError(f"model load failed: {e}") from e

    def predict(self, controls: ControlVars) -> OutputVars:
        """Simulator Protocol 준수 (1-인자). SimLoopManager 클로저 사용 강제."""
        raise NotImplementedError("Use predict_for_session() via SimLoopManager closure")

    def _should_call_ml(self, now: float, ctx: SessionContext) -> bool:
        """게이트 판정 + _last_gate_reason set.

        우선순위:
          1) pending_input_flag + debounce 충족 → reason='input'
          2) interval 경과 → reason='interval'
        """
        if ctx.pending_input_flag and (now - ctx.last_input_t) >= DEBOUNCE_SEC:
            ctx._last_gate_reason = "input"
            return True
        if (now - ctx.last_ml_call_t) >= ML_INTERVAL_SEC:
            ctx._last_gate_reason = "interval"
            return True
        return False
