import json
from pathlib import Path
from unittest.mock import MagicMock

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.main import create_app
from digital_twin.preprocess import FEATURES, TARGETS


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        # 테스트 환경에서는 bootstrap CSV가 부재할 수 있어 SensorBuffer가
        # 빈 상태로 lifespan을 마칠 수 있다. SessionContext.from_sensor_buffer가
        # ValueError를 던지지 않도록 최소 1행 더미를 주입한다.
        buf = getattr(app.state, "sensor_buffer", None)
        if buf is not None and len(buf) == 0:
            buf.load_bootstrap([
                {
                    "syngas_flow": 1500.0, "igv_opening": 75.0,
                    "n2_offset": 200.0, "n2_valve_1": 50.0,
                    "syngas_srv": 60.0, "syngas_gcv_1": 55.0,
                    "syngas_gcv_1a": 55.0, "syngas_gcv_2": 55.0,
                    "ibh_valve": 30.0, "n2_flow": 100.0,
                }
            ])
        yield c


@pytest.fixture
def settings_with_csv():
    """KafkaSensorStream용 settings mock. bootstrap CSV는 기본 경로 사용."""
    settings = MagicMock()
    settings.kafka_stream_enabled = False
    settings.kafka_bootstrap_servers = "localhost:19092"
    settings.kafka_sensor_topic = "noxo.sensor.raw"
    settings.kafka_consumer_group_id = "test"
    settings.kafka_bootstrap_minutes = 15
    settings.kafka_bootstrap_file = None
    return settings


# ============================================================
# ML simulator TDD — 더미 모델 fixture
# ============================================================


@pytest.fixture(scope="session")
def dummy_models_dir(tmp_path_factory) -> Path:
    """학습된 더미 lgb/ridge 모델 + metadata.json 생성.

    session scope — 매번 학습 비용 회피.
    """
    models_dir = tmp_path_factory.mktemp("dummy_models")

    # 단순/빠른 학습용 더미 데이터 — FEATURES 49개 + TARGETS 3개
    rng = np.random.default_rng(seed=42)
    n_samples = 100
    X = pd.DataFrame(
        rng.standard_normal((n_samples, len(FEATURES))),
        columns=FEATURES,
    )
    y = pd.DataFrame(
        rng.standard_normal((n_samples, len(TARGETS))),
        columns=TARGETS,
    )

    # LGB — n_estimators 작게
    fake_lgb = MultiOutputRegressor(LGBMRegressor(n_estimators=5, verbose=-1))
    fake_lgb.fit(X, y)
    joblib.dump(fake_lgb, models_dir / "dt_lgb_model.pkl")

    # Ridge — Pipeline(StandardScaler → Ridge), 실제 metadata 구조 미러
    fake_ridge = MultiOutputRegressor(
        Pipeline([
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=0.01)),
        ])
    )
    fake_ridge.fit(X, y)
    joblib.dump(fake_ridge, models_dir / "dt_ridge_model.pkl")

    # 메타데이터 — 실제 dt_model_metadata.json의 핵심 필드 미러
    meta = {
        "ensemble": {"w_ridge": 0.7, "w_lgb": 0.3, "ridge_alpha": 0.01},
        "features": list(FEATURES),
        "targets": list(TARGETS),
        "feature_engineering": {"npr_hinge_threshold": 1.256052},
    }
    (models_dir / "dt_model_metadata.json").write_text(json.dumps(meta))

    return models_dir


@pytest.fixture
def patched_models_dir(monkeypatch, dummy_models_dir):
    """digital_twin.predict.MODELS_DIR을 dummy_models_dir로 monkeypatch.

    metadata 로더(_load_metadata)와 load_models()가 더미 산출물을 보도록 한다.
    """
    monkeypatch.setattr("digital_twin.predict.MODELS_DIR", dummy_models_dir)
    return dummy_models_dir


@pytest.fixture
def ml_simulator_with_dummy_models(patched_models_dir):
    """더미 모델이 로드된 MLSimulator 인스턴스.

    Task 0.2 시점에서는 MLSimulator(models_dir=...) 시그니처가
    아직 구현되지 않았을 수 있으므로 lazy import + 호출.
    추후 task에서 시그니처 정합 후 본격 사용된다.
    """
    from app.adapters.simulator.ml import MLSimulator

    return MLSimulator(models_dir=patched_models_dir)
