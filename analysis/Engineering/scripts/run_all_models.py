#!/usr/bin/env python3
"""
모든 모델을 한 번에 학습하고 결과를 추적하는 통합 파이프라인

각 모델마다:
  - 학습 시간 기록
  - 성능 지표 (MAE, RMSE) 계산
  - 메타데이터 JSON 저장
  - 결과 CSV로 요약
"""

import time
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import warnings

warnings.filterwarnings('ignore')

class MLPipeline:
    def __init__(self):
        self.experiments_dir = Path('experiments')
        self.metadata_dir = self.experiments_dir / 'metadata'
        self.models_dir = self.experiments_dir / 'models'
        self.reports_dir = Path('reports')

        # 폴더 생성
        for d in [self.metadata_dir, self.models_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.results = []
        self.exp_counter = len(list(self.metadata_dir.glob('exp_*.json'))) + 1

    def load_data(self):
        """데이터 로드 (synthetic 또는 실제)"""
        print("\n" + "="*70)
        print("📥 데이터 로드 중...")
        print("="*70)

        # Synthetic 데이터 확인
        synthetic_path = Path('../../data/synthetic/synthetic_data.parquet')

        if not synthetic_path.exists():
            print("⚠️ Synthetic 데이터가 없습니다. 생성 중...")
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from generate_synthetic_data import generate_synthetic_data

            df, feature_names = generate_synthetic_data(n_samples=10000)
            synthetic_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(synthetic_path, index=False)
            print(f"✅ 생성 완료: {synthetic_path}")
        else:
            df = pd.read_parquet(synthetic_path)
            print(f"✅ 로드 완료: {synthetic_path}")

        # Feature와 Target 분리
        X = df.drop('IGCC.DeNOX.AT_H1_901_PV', axis=1).values
        y = df['IGCC.DeNOX.AT_H1_901_PV'].values
        feature_names = df.drop('IGCC.DeNOX.AT_H1_901_PV', axis=1).columns.tolist()

        print(f"  Shape: {X.shape}")
        print(f"  Features: {len(feature_names)}")
        print(f"  Target: {y.mean():.2f} ± {y.std():.4f}")

        return X, y, feature_names

    def train_ridge(self, X_train, X_val, X_test, y_train, y_val, y_test, feature_names):
        """Ridge Regression 모델"""
        print("\n" + "-"*70)
        print("🎯 모델 1️⃣: Ridge Regression (Baseline)")
        print("-"*70)

        start_time = time.time()

        model = Ridge(alpha=1.0)
        model.fit(X_train, y_train)

        train_time = time.time() - start_time

        # 예측
        y_pred_train = model.predict(X_train)
        y_pred_val = model.predict(X_val)
        y_pred_test = model.predict(X_test)

        # 성능 평가
        results = self._evaluate(
            model_name='Ridge',
            y_train=(y_train, y_pred_train),
            y_val=(y_val, y_pred_val),
            y_test=(y_test, y_pred_test),
            train_time=train_time,
            feature_names=feature_names
        )

        return model, results

    def train_xgboost(self, X_train, X_val, X_test, y_train, y_val, y_test, feature_names):
        """XGBoost 모델"""
        print("\n" + "-"*70)
        print("🎯 모델 2️⃣: XGBoost (Baseline)")
        print("-"*70)

        import xgboost as xgb

        start_time = time.time()

        model = xgb.XGBRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            early_stopping_rounds=30,
            random_state=42,
            verbose=0,
            n_jobs=-1
        )
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )

        train_time = time.time() - start_time

        # 예측
        y_pred_train = model.predict(X_train)
        y_pred_val = model.predict(X_val)
        y_pred_test = model.predict(X_test)

        results = self._evaluate(
            model_name='XGBoost',
            y_train=(y_train, y_pred_train),
            y_val=(y_val, y_pred_val),
            y_test=(y_test, y_pred_test),
            train_time=train_time,
            feature_names=feature_names
        )

        return model, results

    def train_lightgbm(self, X_train, X_val, X_test, y_train, y_val, y_test, feature_names):
        """LightGBM 모델"""
        print("\n" + "-"*70)
        print("🎯 모델 3️⃣: LightGBM")
        print("-"*70)

        import lightgbm as lgb

        start_time = time.time()

        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

        params = {
            'learning_rate': 0.05,
            'num_leaves': 31,
            'max_depth': -1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'lambda_l1': 0.0,
            'lambda_l2': 0.1,
            'objective': 'regression',
            'metric': 'mae',
            'verbose': -1,
        }

        model = lgb.train(
            params,
            train_data,
            num_boost_round=300,
            valid_sets=[train_data, val_data],
            callbacks=[
                lgb.early_stopping(30),
                lgb.log_evaluation(period=0),
            ],
        )

        train_time = time.time() - start_time

        # 예측
        y_pred_train = model.predict(X_train)
        y_pred_val = model.predict(X_val)
        y_pred_test = model.predict(X_test)

        results = self._evaluate(
            model_name='LightGBM',
            y_train=(y_train, y_pred_train),
            y_val=(y_val, y_pred_val),
            y_test=(y_test, y_pred_test),
            train_time=train_time,
            feature_names=feature_names
        )

        return model, results

    def _evaluate(self, model_name, y_train, y_val, y_test, train_time, feature_names):
        """모델 평가 및 결과 기록"""
        y_true_train, y_pred_train = y_train
        y_true_val, y_pred_val = y_val
        y_true_test, y_pred_test = y_test

        metrics = {
            'train_mae': mean_absolute_error(y_true_train, y_pred_train),
            'train_rmse': np.sqrt(mean_squared_error(y_true_train, y_pred_train)),
            'val_mae': mean_absolute_error(y_true_val, y_pred_val),
            'val_rmse': np.sqrt(mean_squared_error(y_true_val, y_pred_val)),
            'test_mae': mean_absolute_error(y_true_test, y_pred_test),
            'test_rmse': np.sqrt(mean_squared_error(y_true_test, y_pred_test)),
        }

        # 출력
        print(f"  ⏱️ 학습 시간: {train_time:.2f}초")
        print(f"  📊 Train MAE: {metrics['train_mae']:.6f}")
        print(f"  📊 Val MAE:   {metrics['val_mae']:.6f}")
        print(f"  🎯 Test MAE:  {metrics['test_mae']:.6f}")

        # 메타데이터 생성
        exp_id = f"exp_{self.exp_counter:03d}_{model_name.lower()}"
        self.exp_counter += 1

        metadata = {
            'experiment_id': exp_id,
            'model': model_name,
            'timestamp': datetime.now().isoformat(),
            'training_time_seconds': train_time,
            'performance': metrics,
            'n_features': len(feature_names),
        }

        # 메타데이터 저장
        metadata_path = self.metadata_dir / f"{exp_id}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # 결과 추가
        self.results.append({
            'Exp_ID': exp_id,
            'Model': model_name,
            'Train_MAE': metrics['train_mae'],
            'Val_MAE': metrics['val_mae'],
            'Test_MAE': metrics['test_mae'],
            'Test_RMSE': metrics['test_rmse'],
            'Training_Time_sec': train_time,
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })

        print(f"  ✅ 저장 완료: {metadata_path}")

        return metrics

    def run(self):
        """전체 파이프라인 실행"""
        print("\n🚀 NOx 예측 AI 엔지니어링 시작")
        print("="*70)

        # 데이터 로드
        X, y, feature_names = self.load_data()

        # 시계열 데이터이므로 시간순 분할 (shuffle=False)
        split1 = int(len(X) * 0.7)
        split2 = int(len(X) * 0.85)

        X_train = X[:split1]
        y_train = y[:split1]

        X_val = X[split1:split2]
        y_val = y[split1:split2]

        X_test = X[split2:]
        y_test = y[split2:]

        print(f"\n📊 데이터 분할")
        print(f"  Train: {len(X_train):,}")
        print(f"  Val: {len(X_val):,}")
        print(f"  Test: {len(X_test):,}")

        # 모델 학습
        try:
            self.train_ridge(X_train, X_val, X_test, y_train, y_val, y_test, feature_names)
        except Exception as e:
            print(f"❌ Ridge 오류: {e}")

        try:
            self.train_xgboost(X_train, X_val, X_test, y_train, y_val, y_test, feature_names)
        except Exception as e:
            print(f"❌ XGBoost 오류: {e}")

        try:
            self.train_lightgbm(X_train, X_val, X_test, y_train, y_val, y_test, feature_names)
        except Exception as e:
            print(f"❌ LightGBM 오류: {e}")

        # 결과 요약
        self._save_summary()

    def _save_summary(self):
        """결과 요약 저장"""
        print("\n" + "="*70)
        print("📋 결과 요약")
        print("="*70)

        df_results = pd.DataFrame(self.results)

        # CSV로 저장
        summary_path = self.experiments_dir / 'results_summary.csv'
        df_results.to_csv(summary_path, index=False, encoding='utf-8-sig')

        print(f"\n✅ 결과 저장: {summary_path}\n")
        print(df_results.to_string(index=False))

        # 최고 성능 모델
        best_idx = df_results['Test_MAE'].idxmin()
        best_model = df_results.iloc[best_idx]

        print(f"\n🏆 최고 성능 모델: {best_model['Model']}")
        print(f"   Test MAE: {best_model['Test_MAE']:.6f}")
        print(f"   학습 시간: {best_model['Training_Time_sec']:.2f}초")

if __name__ == '__main__':
    pipeline = MLPipeline()
    pipeline.run()
