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

        Phase 0 #B1: 모델 출력이 정규화된 경우 본 메서드에서 역변환.
        현재는 원본 스케일 가정.

        R-A8 / K5 (4차 보강) — lambda_/efficiency 처리 책임 분리 cross-ref:
        - lambda_: DT engine의 `compute_lambda(state.current)` (Zeldovich ODE에 필요한 stoichiometric ratio)가
          매 sim_step에서 OutputVars.lambda_를 덮어쓴다. 본 메서드 반환의 0.0은 즉시 무시됨.
        - efficiency: `apps/backend/app/core/sim_loop.py`의 LHV 후처리 단계가 `power/(syngas_flow × syngas_lhv)`로
          계산하여 broadcast 직전에 덮어쓴다. 본 메서드 반환의 0.0도 즉시 무시됨.
        → 두 필드는 ML 모델 학습 타깃이 아니므로 명시적 dummy(0.0)로 두고 downstream이 책임진다.
        """
        return OutputVars(
            nox=result["IGCC.DeNOX.AT_H1_901_PV"],
            exhaust_temp=result["IGCC.CC.G1.TTXM"],
            power=result["IGCC.CC.G1.DWATT"],
            lambda_=0.0,      # engine.py compute_lambda 덮어씀 (R-A8/K5 — 위 docstring 참조)
            efficiency=0.0,   # sim_loop LHV 후처리 덮어씀 (R-A8/K5 — 위 docstring 참조)
        )
