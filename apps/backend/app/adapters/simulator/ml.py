"""ML 기반 Simulator — Ridge·LGB 앙상블.

Simulator Protocol(외부): predict(controls) — NotImplementedError. RealtimeEngine이 클로저로 ctx 바인딩.
실제 추론 본체: predict_for_session(controls, session_ctx).
"""

import time
import warnings
from pathlib import Path

from digital_twin.simulation import ControlVars, OutputVars
from digital_twin.predict import predict as dt_predict
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
        """Simulator Protocol 준수 (1-인자). RealtimeEngine이 ctx-bound 호출 사용."""
        raise NotImplementedError("Use predict_for_session() via RealtimeEngine closure")

    def predict_for_session(
        self, controls: ControlVars, session_ctx: SessionContext
    ) -> OutputVars:
        """실제 추론 본체. RealtimeEngine이 `simulator.predict_for_session(c, ctx)`로 호출."""
        now = time.monotonic()

        # [1] 호출 게이트 (P4 — conditional raise)
        if not self._should_call_ml(now, session_ctx):
            if session_ctx.cached_output_target is None:
                raise SessionTerminatedError(
                    "cache_invariant_violation: SessionService가 초기 ML 호출로 cache를 채워야 함"
                )
            return session_ctx.cached_output_target

        # [2] RAW 39 + TTXM 단일 행 + [3] dt_predict 호출
        try:
            current_row = self._build_current_row(controls, session_ctx)
            with warnings.catch_warnings():
                # T9 — warm-up UserWarning suppression (세션당 1회만 로그)
                warnings.simplefilter("ignore", UserWarning)
                result = dt_predict(
                    model=(self.lgb, self.ridge),
                    inputs=current_row,
                    recent_df=session_ctx.buffer_to_df(),
                )
        except Exception as e:
            session_ctx.ml_failure_count += 1
            if session_ctx.ml_failure_count >= ML_MAX_FAILURES:
                raise SessionTerminatedError(f"ml_failure_threshold_exceeded: {e}") from e
            # C5 — cached invariant guard
            if session_ctx.cached_output_target is None:
                raise SessionTerminatedError(
                    "ml_failed_with_no_cache: invariant violation"
                ) from e
            return session_ctx.cached_output_target

        session_ctx.ml_failure_count = 0

        # [5] 결과 매핑 + ctx 갱신
        output_target = self._result_to_outputvars(result)
        session_ctx.cached_output_target = output_target
        session_ctx.last_ml_call_t = now
        # C4 — input 게이트일 때만 pending reset
        if session_ctx._last_gate_reason == "input":
            session_ctx.pending_input_flag = False
        return output_target

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

    def _build_current_row(self, controls: ControlVars, ctx: SessionContext):
        """RAW 39 + TTXM 1 = 40컬럼 단일 행 DataFrame.

        plant_context(외란 29 + TTXM 1) ∪ controls(10) = 40 키 (disjoint).
        예측 컬럼 순서는 RAW_FEATURES + TTXM.
        """
        import pandas as pd
        from app.domain.tags import control_vars_to_tag_dict
        from digital_twin.preprocess import RAW_FEATURES

        controls_dict = control_vars_to_tag_dict(controls)
        row = {**ctx.plant_context, **controls_dict}
        TTXM_COL = "IGCC.CC.G1.TTXM"
        return pd.DataFrame([{k: row[k] for k in list(RAW_FEATURES) + [TTXM_COL]}])

    def _result_to_outputvars(self, result: dict) -> OutputVars:
        """dt_predict dict 결과 → OutputVars.

        lambda_/efficiency 후처리 책임 — RealtimeEngine._postprocess_outputs로 일원화.
        본 메서드는 ML 학습 타깃이 아닌 두 필드를 dummy(0.0)로 반환하고,
        RealtimeEngine이 compute_lambda + power/(syngas_flow×LHV)로 덮어쓴다.
        """
        return OutputVars(
            nox=result["IGCC.DeNOX.AT_H1_901_PV"],
            exhaust_temp=result["IGCC.CC.G1.TTXM"],
            power=result["IGCC.CC.G1.DWATT"],
            lambda_=0.0,      # RealtimeEngine._postprocess_outputs가 덮어씀
            efficiency=0.0,   # RealtimeEngine._postprocess_outputs가 덮어씀
        )
