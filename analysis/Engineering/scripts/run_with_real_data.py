#!/usr/bin/env python3
"""
실제 데이터로 모든 모델을 학습하고 비교하는 스크립트
데이터: NOxO/data/의 실제 IGCC 센서 데이터
"""

import time
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import warnings

warnings.filterwarnings('ignore')

class RealDataMLPipeline:
    def __init__(self):
        self.experiments_dir = Path('experiments')
        self.metadata_dir = self.experiments_dir / 'metadata'
        self.reports_dir = Path('reports')

        for d in [self.metadata_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.results = []
        self.exp_counter = len(list(self.metadata_dir.glob('exp_*.json'))) + 1

    def load_real_data(self):
        """실제 데이터 로드 및 전처리"""
        print("\n" + "="*70)
        print("📥 실제 데이터 로드 중... (NOxO/data/)")
        print("="*70)

        # 데이터 경로
        file1 = Path('/Users/gimhuitae/공모전/NOxO/data/20250811_000000-20250825_235959_00001.csv')
        file2 = Path('/Users/gimhuitae/공모전/NOxO/data/20250811_000000-20250825_235959_00002.csv')

        if not file1.exists() or not file2.exists():
            print("❌ 실제 데이터 파일을 찾을 수 없습니다")
            return None

        print(f"📖 로드 중: {file1.name} (386MB)")
        df1 = pd.read_csv(file1, skiprows=[1,2,3,4], low_memory=False)  # 메타데이터 건너뛰기

        print(f"📖 로드 중: {file2.name} (114MB)")
        df2 = pd.read_csv(file2, skiprows=[1,2,3,4], low_memory=False)

        print(f"✅ 로드 완료")
        print(f"  File 1: {len(df1):,}행")
        print(f"  File 2: {len(df2):,}행")

        # TagName, 불필요한 컬럼 제거
        df1 = df1.drop('TagName', axis=1, errors='ignore')
        df2 = df2.drop('TagName', axis=1, errors='ignore')

        # 두 파일 합치기
        df = pd.concat([df1, df2], ignore_index=True)
        print(f"  Total: {len(df):,}행")

        # 100% 결측치 컬럼 제거
        missing_pct = df.isnull().sum() / len(df) * 100
        cols_to_drop = missing_pct[missing_pct == 100].index.tolist()
        if cols_to_drop:
            df = df.drop(cols_to_drop, axis=1)
            print(f"  불필요한 컬럼 제거: {cols_to_drop}")

        # 타깃 변수 찾기
        target_col = 'IGCC.DeNOX.AT_H1_901_PV'  # NOx 농도

        if target_col not in df.columns:
            print(f"❌ 타깃 컬럼 '{target_col}'을 찾을 수 없습니다")
            print(f"  사용 가능한 컬럼: {df.columns.tolist()[:10]}")
            return None

        # 타깃 확인
        print(f"\n🎯 타깃 변수 통계:")
        print(f"  컬럼: {target_col}")
        print(f"  평균: {df[target_col].mean():.2f}")
        print(f"  표준편차: {df[target_col].std():.2f}")
        print(f"  범위: {df[target_col].min():.2f} ~ {df[target_col].max():.2f}")

        # 결측치 제거
        initial_len = len(df)
        df = df.dropna()
        print(f"\n📊 결측치 처리:")
        print(f"  제거 전: {initial_len:,}행")
        print(f"  제거 후: {len(df):,}행")

        # 피처와 타깃 분리
        X = df.drop(target_col, axis=1).astype(float).values
        y = df[target_col].astype(float).values
        feature_names = df.drop(target_col, axis=1).columns.tolist()

        print(f"\n📈 데이터셋 정보:")
        print(f"  피처 수: {X.shape[1]}")
        print(f"  샘플 수: {X.shape[0]:,}")

        return X, y, feature_names

    def train_ridge(self, X_train, X_val, X_test, y_train, y_val, y_test):
        """Ridge Regression"""
        print("\n" + "-"*70)
        print("🎯 모델: Ridge Regression (실제 데이터)")
        print("-"*70)

        start_time = time.time()

        model = Ridge(alpha=1.0)
        model.fit(X_train, y_train)

        train_time = time.time() - start_time

        y_pred_train = model.predict(X_train)
        y_pred_val = model.predict(X_val)
        y_pred_test = model.predict(X_test)

        self._evaluate(
            model_name='Ridge_RealData',
            y_train=(y_train, y_pred_train),
            y_val=(y_val, y_pred_val),
            y_test=(y_test, y_pred_test),
            train_time=train_time
        )

    def train_lightgbm(self, X_train, X_val, X_test, y_train, y_val, y_test):
        """LightGBM"""
        print("\n" + "-"*70)
        print("🎯 모델: LightGBM (실제 데이터)")
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

        y_pred_train = model.predict(X_train)
        y_pred_val = model.predict(X_val)
        y_pred_test = model.predict(X_test)

        self._evaluate(
            model_name='LightGBM_RealData',
            y_train=(y_train, y_pred_train),
            y_val=(y_val, y_pred_val),
            y_test=(y_test, y_pred_test),
            train_time=train_time
        )

    def train_xgboost(self, X_train, X_val, X_test, y_train, y_val, y_test):
        """XGBoost"""
        print("\n" + "-"*70)
        print("🎯 모델: XGBoost (실제 데이터)")
        print("-"*70)

        try:
            import xgboost as xgb
        except ImportError:
            print("❌ XGBoost not installed")
            return

        start_time = time.time()

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
            model_name='XGBoost_RealData',
            y_train=(y_train, y_pred_train),
            y_val=(y_val, y_pred_val),
            y_test=(y_test, y_pred_test),
            train_time=train_time
        )

    def _evaluate(self, model_name, y_train, y_val, y_test, train_time):
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

        exp_id = f"exp_{self.exp_counter:03d}_{model_name.lower()}"
        self.exp_counter += 1

        metadata = {
            'experiment_id': exp_id,
            'model': model_name,
            'timestamp': datetime.now().isoformat(),
            'training_time_seconds': train_time,
            'performance': metrics,
            'data_type': 'real_data',
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

        print(f"  ✅ 저장: {metadata_path}")

    def run(self):
        """실행"""
        print("\n🚀 실제 데이터로 모델 학습 시작")
        print("="*70)

        # 데이터 로드
        data = self.load_real_data()
        if data is None:
            return

        X, y, feature_names = data

        # 시계열 분할 (시간순)
        split1 = int(len(X) * 0.7)
        split2 = int(len(X) * 0.85)

        X_train, X_val, X_test = X[:split1], X[split1:split2], X[split2:]
        y_train, y_val, y_test = y[:split1], y[split1:split2], y[split2:]

        print(f"\n📊 데이터 분할:")
        print(f"  Train: {len(X_train):,}행")
        print(f"  Val: {len(X_val):,}행")
        print(f"  Test: {len(X_test):,}행")

        # 모델 학습
        models = [
            (self.train_ridge, "Ridge"),
            (self.train_lightgbm, "LightGBM"),
            (self.train_xgboost, "XGBoost"),
        ]

        for train_func, name in models:
            try:
                train_func(X_train, X_val, X_test, y_train, y_val, y_test)
            except Exception as e:
                print(f"❌ {name} 오류: {e}")

        # 결과 저장
        self._save_results()

    def _save_results(self):
        """결과 저장"""
        print("\n" + "="*70)
        print("📋 실제 데이터 실험 결과")
        print("="*70)

        df_results = pd.DataFrame(self.results)

        # 기존 결과에 추가
        summary_path = self.experiments_dir / 'results_summary.csv'
        if summary_path.exists():
            df_existing = pd.read_csv(summary_path)
            df_all = pd.concat([df_existing, df_results], ignore_index=True)
        else:
            df_all = df_results

        df_all.to_csv(summary_path, index=False, encoding='utf-8-sig')

        print(f"\n✅ 결과 저장: {summary_path}\n")
        print(df_results.to_string(index=False))

        # 최고 성능
        if len(df_results) > 0:
            best_idx = df_results['Test_MAE'].idxmin()
            best_model = df_results.iloc[best_idx]

            print(f"\n🏆 최고 성능 모델 (실제 데이터):")
            print(f"   모델: {best_model['Model']}")
            print(f"   Test MAE: {best_model['Test_MAE']:.6f}")
            print(f"   학습 시간: {best_model['Training_Time_sec']:.2f}초")

if __name__ == '__main__':
    pipeline = RealDataMLPipeline()
    pipeline.run()
