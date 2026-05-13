"""Ridge + LightGBM 가중 앙상블 컨테이너.

joblib pickle 호환을 위해 별도 모듈에 정의 — train.py와 predict.py가
이 클래스를 동일 경로로 import해야 unpickle 가능.
"""

from __future__ import annotations

import numpy as np


class EnsembleForecaster:
    """Ridge + LGB 가중 앙상블. joblib.dump로 단일 객체 저장."""

    def __init__(self, ridge_pipe, lgb, w_ridge: float):
        self.ridge_pipe = ridge_pipe
        self.lgb = lgb
        self.w_ridge = float(w_ridge)

    def predict(self, X) -> np.ndarray:
        y_r = self.ridge_pipe.predict(X)
        y_l = self.lgb.predict(X)
        return self.w_ridge * y_r + (1.0 - self.w_ridge) * y_l

    @property
    def feature_importances_(self) -> np.ndarray:
        """LGB feature importance 그대로 노출."""
        return self.lgb.feature_importances_


__all__ = ["EnsembleForecaster"]
