#!/usr/bin/env python3
"""
NOx 예측 AI 엔지니어링 - 통합 실험 실행 스크립트

사용법:
  python run_experiment.py --config configs/exp_lightgbm_v1.yaml
  python run_experiment.py --mode baseline_reproduction
  python run_experiment.py --config configs/exp_lightgbm_v1.yaml --save_model
"""

import argparse
import yaml
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExperimentRunner:
    """실험 실행 및 추적"""

    def __init__(self, config_path: str, baseline_dir: str = "../nox_manual_baseline"):
        self.config_path = Path(config_path)
        self.baseline_dir = Path(baseline_dir)
        self.config = self._load_config()
        self.experiments_dir = Path("experiments")
        self.experiments_dir.mkdir(exist_ok=True)

        # 실험 ID 생성
        self.exp_id = self._generate_exp_id()

        logger.info(f"✅ Experiment initialized: {self.exp_id}")

    def _load_config(self) -> Dict[str, Any]:
        """YAML 설정 파일 로드"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _generate_exp_id(self) -> str:
        """실험 ID 생성 (exp_001, exp_002, ...)"""
        metadata_dir = self.experiments_dir / "metadata"
        metadata_dir.mkdir(exist_ok=True)

        existing = list(metadata_dir.glob("exp_*.json"))
        exp_num = len(existing) + 1
        model_type = self.config['model']['type'].lower()
        return f"exp_{exp_num:03d}_{model_type}_v1"

    def load_data(self) -> tuple:
        """
        데이터 로드
        Note: 실제 구현에서는 전처리된 parquet 파일 로드
        """
        logger.info("📁 Loading data...")

        # 임시: 베이스라인 데이터 경로
        data_path = self.baseline_dir / "data" / "processed" / "normalized_train.parquet"

        if not data_path.exists():
            logger.warning(f"⚠️ Data not found at {data_path}")
            logger.info("💡 Run nox_manual_baseline stage 00P first")
            return None, None, None, None

        df = pd.read_parquet(data_path)

        # Feature와 Target 분리
        feature_cols = [col for col in df.columns
                       if col not in ['IGCC.DeNOX.AT_H1_901_PV', 'timestamp']]
        target_col = 'IGCC.DeNOX.AT_H1_901_PV'

        X = df[feature_cols].values
        y = df[target_col].values

        # 시간순 분할 (shuffle=False 필수)
        test_size = self.config['train'].get('test_size', 0.2)
        split_idx = int(len(X) * (1 - test_size))

        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        logger.info(f"  Train: {len(X_train)}, Test: {len(X_test)}")

        return X_train, X_test, y_train, y_test, feature_cols

    def train_model(self, X_train, y_train, X_val, y_val):
        """모델 학습"""
        model_type = self.config['model']['type']
        logger.info(f"🚀 Training {model_type.upper()}...")

        if model_type == 'ridge':
            from sklearn.linear_model import Ridge
            model = Ridge(alpha=self.config['parameters']['alpha'])
            model.fit(X_train, y_train)

        elif model_type == 'lightgbm':
            import lightgbm as lgb

            train_data = lgb.Dataset(X_train, label=y_train)
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

            params = {
                'learning_rate': self.config['parameters']['learning_rate'],
                'num_leaves': self.config['parameters']['num_leaves'],
                'max_depth': self.config['parameters']['max_depth'],
                'subsample': self.config['parameters']['subsample'],
                'colsample_bytree': self.config['parameters']['colsample_bytree'],
                'lambda_l1': self.config['parameters']['lambda_l1'],
                'lambda_l2': self.config['parameters']['lambda_l2'],
                'min_child_samples': self.config['parameters']['min_child_samples'],
                'objective': 'regression',
                'metric': 'mae',
                'verbose': -1,
            }

            model = lgb.train(
                params,
                train_data,
                num_boost_round=self.config['parameters']['n_estimators'],
                valid_sets=[train_data, val_data],
                callbacks=[
                    lgb.early_stopping(self.config['training']['early_stopping_rounds']),
                    lgb.log_evaluation(period=50),
                ],
            )

        else:
            raise ValueError(f"Unknown model type: {model_type}")

        logger.info("✅ Training completed")
        return model

    def evaluate_model(self, model, X_train, X_test, y_train, y_test) -> Dict[str, float]:
        """모델 평가"""
        logger.info("📊 Evaluating model...")

        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)

        results = {
            'train_mae': mean_absolute_error(y_train, y_pred_train),
            'train_rmse': np.sqrt(mean_squared_error(y_train, y_pred_train)),
            'test_mae': mean_absolute_error(y_test, y_pred_test),
            'test_rmse': np.sqrt(mean_squared_error(y_test, y_pred_test)),
        }

        logger.info(f"  Train MAE: {results['train_mae']:.4f}")
        logger.info(f"  Test MAE: {results['test_mae']:.4f}")

        return results

    def save_experiment(self, model, results, feature_cols):
        """실험 결과 저장"""
        metadata_dir = self.experiments_dir / "metadata"
        metadata_dir.mkdir(exist_ok=True)

        models_dir = self.experiments_dir / "models"
        models_dir.mkdir(exist_ok=True)

        # 메타데이터 생성
        metadata = {
            'experiment_id': self.exp_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'completed',
            'model_info': self.config['model'],
            'performance': results,
            'data_info': {
                'n_features': len(feature_cols),
                'feature_selection': self.config['data']['features'],
            },
            'config_file': str(self.config_path),
        }

        # JSON 저장
        metadata_path = metadata_dir / f"{self.exp_id}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Metadata saved: {metadata_path}")

        # 모델 저장
        model_path = models_dir / f"{self.exp_id}.pkl"
        import joblib
        joblib.dump(model, model_path)
        logger.info(f"✅ Model saved: {model_path}")

        return metadata

    def run(self):
        """전체 실험 실행"""
        logger.info(f"=" * 60)
        logger.info(f"🎯 Running experiment: {self.exp_id}")
        logger.info(f"=" * 60)

        # 데이터 로드
        data = self.load_data()
        if data[0] is None:
            logger.error("❌ Failed to load data")
            return

        X_train, X_test, y_train, y_test, feature_cols = data

        # Validation split
        val_split = int(len(X_train) * 0.2)
        X_train_sub, X_val = X_train[:-val_split], X_train[-val_split:]
        y_train_sub, y_val = y_train[:-val_split], y_train[-val_split:]

        # 모델 학습
        model = self.train_model(X_train_sub, y_train_sub, X_val, y_val)

        # 평가
        results = self.evaluate_model(model, X_train, X_test, y_train, y_test)

        # 저장
        self.save_experiment(model, results, feature_cols)

        logger.info(f"=" * 60)
        logger.info(f"✅ Experiment completed successfully!")
        logger.info(f"=" * 60)


def main():
    parser = argparse.ArgumentParser(description='NOx 예측 AI 엔지니어링 - 실험 실행')
    parser.add_argument('--config', type=str, default='configs/baseline_ridge.yaml',
                       help='Configuration file path')
    parser.add_argument('--mode', type=str, choices=['baseline_reproduction', 'custom'],
                       default='custom', help='Running mode')

    args = parser.parse_args()

    runner = ExperimentRunner(args.config)
    runner.run()


if __name__ == '__main__':
    main()
