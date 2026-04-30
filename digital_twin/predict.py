import joblib
import pandas as pd
from pathlib import Path
from preprocess import FEATURES, TARGETS

MODELS_DIR = Path(__file__).parent / "models"


def load_model(model_path: Path | None = None) -> object:
    path = Path(model_path) if model_path else MODELS_DIR / "dt_multi_model.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {path}")
    return joblib.load(path)


def predict(model: object, inputs: dict | pd.DataFrame) -> dict:
    if isinstance(inputs, dict):
        df = pd.DataFrame([inputs])[FEATURES]
    else:
        df = inputs[FEATURES].head(1)

    y_pred = model.predict(df)
    return {target: float(y_pred[0, i]) for i, target in enumerate(TARGETS)}
