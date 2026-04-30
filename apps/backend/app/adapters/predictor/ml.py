"""실제 ML 모델 기반 Predictor — placeholder.

추후 digital_twin/models/*.pkl 또는 별도 학습 산출물을 로드하여 본 모듈을 채운다.
인터페이스는 `app.adapters.predictor.base.Predictor`를 따른다.
"""

from digital_twin.simulation import ControlVars, OutputVars
from app.exceptions import PredictorUnavailableError


class MLPredictor:
    name = "ml"

    def __init__(self, model_path: str):
        self.model_path = model_path
        # TODO: joblib.load 등으로 모델 로드

    def predict(self, controls: ControlVars) -> OutputVars:
        raise PredictorUnavailableError(
            "ML predictor not implemented yet — wire digital_twin model here."
        )
