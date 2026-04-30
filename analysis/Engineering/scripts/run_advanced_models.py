#!/usr/bin/env python3
"""
고급 모델들 추가 학습 (XGBoost 수정, TabNet, Neural Network 등)
"""

import time
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')

class AdvancedMLPipeline:
    def __init__(self):
        self.experiments_dir = Path('experiments')
        self.metadata_dir = self.experiments_dir / 'metadata'
        self.models_dir = self.experiments_dir / 'models'
        self.reports_dir = Path('reports')

        for d in [self.metadata_dir, self.models_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.results = []
        self.exp_counter = len(list(self.metadata_dir.glob('exp_*.json'))) + 1

    def load_data(self):
        """데이터 로드"""
        print("\n📥 데이터 로드 중...")

        data_path = Path('../../data/synthetic/synthetic_data.parquet')
        df = pd.read_parquet(data_path)

        X = df.drop('IGCC.DeNOX.AT_H1_901_PV', axis=1).values
        y = df['IGCC.DeNOX.AT_H1_901_PV'].values
        feature_names = df.drop('IGCC.DeNOX.AT_H1_901_PV', axis=1).columns.tolist()

        # 시계열 분할
        split1 = int(len(X) * 0.7)
        split2 = int(len(X) * 0.85)

        return (X[:split1], X[split1:split2], X[split2:],
                y[:split1], y[split1:split2], y[split2:],
                feature_names)

    def train_xgboost_fixed(self, X_train, X_val, X_test, y_train, y_val, y_test, feature_names):
        """XGBoost 모델 (수정된 버전)"""
        print("\n" + "-"*70)
        print("🎯 모델: XGBoost (수정된 버전)")
        print("-"*70)

        try:
            import xgboost as xgb
        except ImportError:
            print("❌ XGBoost not installed")
            return

        start_time = time.time()

        # XGBoost 1.5+ 문법 사용
        model = xgb.XGBRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=0,
            n_jobs=-1
        )

        # early_stopping은 fit 파라미터로 전달
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )

        train_time = time.time() - start_time

        y_pred_train = model.predict(X_train)
        y_pred_val = model.predict(X_val)
        y_pred_test = model.predict(X_test)

        self._evaluate(
            model_name='XGBoost',
            y_train=(y_train, y_pred_train),
            y_val=(y_val, y_pred_val),
            y_test=(y_test, y_pred_test),
            train_time=train_time,
            feature_names=feature_names
        )

    def train_gradient_boosting(self, X_train, X_val, X_test, y_train, y_val, y_test, feature_names):
        """Scikit-learn GradientBoosting"""
        print("\n" + "-"*70)
        print("🎯 모델: Gradient Boosting (Scikit-learn)")
        print("-"*70)

        from sklearn.ensemble import GradientBoostingRegressor

        start_time = time.time()

        model = GradientBoostingRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.8,
            random_state=42,
            verbose=0
        )

        model.fit(X_train, y_train)
        train_time = time.time() - start_time

        y_pred_train = model.predict(X_train)
        y_pred_val = model.predict(X_val)
        y_pred_test = model.predict(X_test)

        self._evaluate(
            model_name='GradientBoosting',
            y_train=(y_train, y_pred_train),
            y_val=(y_val, y_pred_val),
            y_test=(y_test, y_pred_test),
            train_time=train_time,
            feature_names=feature_names
        )

    def train_random_forest(self, X_train, X_val, X_test, y_train, y_val, y_test, feature_names):
        """Random Forest"""
        print("\n" + "-"*70)
        print("🎯 모델: Random Forest")
        print("-"*70)

        from sklearn.ensemble import RandomForestRegressor

        start_time = time.time()

        model = RandomForestRegressor(
            n_estimators=300,
            max_depth=20,
            random_state=42,
            n_jobs=-1,
            verbose=0
        )

        model.fit(X_train, y_train)
        train_time = time.time() - start_time

        y_pred_train = model.predict(X_train)
        y_pred_val = model.predict(X_val)
        y_pred_test = model.predict(X_test)

        self._evaluate(
            model_name='RandomForest',
            y_train=(y_train, y_pred_train),
            y_val=(y_val, y_pred_val),
            y_test=(y_test, y_pred_test),
            train_time=train_time,
            feature_names=feature_names
        )

    def train_svr(self, X_train, X_val, X_test, y_train, y_val, y_test, feature_names):
        """Support Vector Regression"""
        print("\n" + "-"*70)
        print("🎯 모델: Support Vector Regression (SVR)")
        print("-"*70)

        from sklearn.svm import SVR
        from sklearn.preprocessing import StandardScaler

        # SVR은 정규화 필수
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        X_test_scaled = scaler.transform(X_test)

        start_time = time.time()

        model = SVR(kernel='rbf', C=100, epsilon=0.01)
        model.fit(X_train_scaled, y_train)

        train_time = time.time() - start_time

        y_pred_train = model.predict(X_train_scaled)
        y_pred_val = model.predict(X_val_scaled)
        y_pred_test = model.predict(X_test_scaled)

        self._evaluate(
            model_name='SVR',
            y_train=(y_train, y_pred_train),
            y_val=(y_val, y_pred_val),
            y_test=(y_test, y_pred_test),
            train_time=train_time,
            feature_names=feature_names
        )

    def _evaluate(self, model_name, y_train, y_val, y_test, train_time, feature_names):
        """평가 및 기록"""
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

        print(f"  ⏱️ 학습 시간: {train_time:.2f}초")
        print(f"  📊 Train MAE: {metrics['train_mae']:.6f}")
        print(f"  📊 Val MAE:   {metrics['val_mae']:.6f}")
        print(f"  🎯 Test MAE:  {metrics['test_mae']:.6f}")

        exp_id = f"exp_{self.exp_counter:03d}_{model_name.lower().replace(' ', '_')}"
        self.exp_counter += 1

        metadata = {
            'experiment_id': exp_id,
            'model': model_name,
            'timestamp': datetime.now().isoformat(),
            'training_time_seconds': train_time,
            'performance': metrics,
        }

        metadata_path = self.metadata_dir / f"{exp_id}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

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

    def run(self):
        """모든 모델 실행"""
        print("\n🚀 고급 모델 학습 시작")
        print("="*70)

        X_train, X_val, X_test, y_train, y_val, y_test, feature_names = self.load_data()

        # 모델들 학습
        models_to_train = [
            (self.train_xgboost_fixed, "XGBoost"),
            (self.train_gradient_boosting, "Gradient Boosting"),
            (self.train_random_forest, "Random Forest"),
            (self.train_svr, "SVR"),
        ]

        for train_func, name in models_to_train:
            try:
                train_func(X_train, X_val, X_test, y_train, y_val, y_test, feature_names)
            except Exception as e:
                print(f"❌ {name} 오류: {e}")

        # 전체 결과 요약
        self._save_all_results()

    def _save_all_results(self):
        """전체 결과 요약"""
        print("\n" + "="*70)
        print("📋 전체 결과 요약")
        print("="*70)

        # 기존 결과 로드
        summary_path = self.experiments_dir / 'results_summary.csv'
        if summary_path.exists():
            df_existing = pd.read_csv(summary_path)
            df_all = pd.concat([df_existing, pd.DataFrame(self.results)], ignore_index=True)
        else:
            df_all = pd.DataFrame(self.results)

        # 저장
        df_all.to_csv(summary_path, index=False, encoding='utf-8-sig')

        print(f"\n✅ 결과 저장: {summary_path}\n")
        print(df_all.sort_values('Test_MAE').to_string(index=False))

        # 순위
        print(f"\n🏆 성능 순위 (Test MAE 기준):")
        for i, row in df_all.nsmallest(5, 'Test_MAE').iterrows():
            print(f"   {row['Model']:20s} Test MAE: {row['Test_MAE']:.6f} ({row['Training_Time_sec']:6.2f}초)")

if __name__ == '__main__':
    pipeline = AdvancedMLPipeline()
    pipeline.run()
