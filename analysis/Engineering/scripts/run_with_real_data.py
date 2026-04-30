#!/usr/bin/env python3
"""
실제 데이터로 모든 모델을 학습하고 비교하는 스크립트
Train: NOx_train_20250811_20250824.csv
Test:  NOx_test_20250825.csv
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

DATA_DIR = Path('/Users/gimhuitae/공모전/NOxO/data')
TRAIN_FILE = DATA_DIR / 'NOx_train_20250811_20250824.csv'
TEST_FILE  = DATA_DIR / 'NOx_test_20250825.csv'

TARGET_COL = 'IGCC.DeNOX.AT_H1_901_PV'
META_ROWS  = [1, 2, 3, 4]  # Description / Units / Plot Min / Plot Max


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, skiprows=META_ROWS, encoding='utf-8-sig', low_memory=False)
    df = df.drop(columns=['TagName', 'Column1'], errors='ignore')
    return df


class RealDataMLPipeline:
    def __init__(self):
        self.experiments_dir = Path('experiments')
        self.metadata_dir = self.experiments_dir / 'metadata'
        self.reports_dir = Path('reports')

        for d in [self.metadata_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.results = []
        self.exp_counter = len(list(self.metadata_dir.glob('exp_*.json'))) + 1

    def load_data(self):
        print("\n" + "="*70)
        print("📥 실제 데이터 로드 중...")
        print("="*70)

        for f in [TRAIN_FILE, TEST_FILE]:
            if not f.exists():
                print(f"❌ 파일 없음: {f}")
                return None

        print(f"📖 Train: {TRAIN_FILE.name} ({TRAIN_FILE.stat().st_size / 1e6:.0f}MB)")
        df_train_all = load_csv(TRAIN_FILE)

        print(f"📖 Test:  {TEST_FILE.name} ({TEST_FILE.stat().st_size / 1e6:.0f}MB)")
        df_test = load_csv(TEST_FILE)

        print(f"  Train rows: {len(df_train_all):,}")
        print(f"  Test  rows: {len(df_test):,}")

        # 타깃 확인
        for df, name in [(df_train_all, 'Train'), (df_test, 'Test')]:
            if TARGET_COL not in df.columns:
                print(f"❌ '{TARGET_COL}' 컬럼 없음 ({name})")
                print(f"   사용 가능 컬럼: {df.columns.tolist()[:10]}")
                return None

        print(f"\n📊 결측치 제거 후 - Train: {len(df_train_all):,}행 / Test: {len(df_test):,}행 (numeric 변환 전)")

        # 타깃 통계
        print(f"\n🎯 타깃({TARGET_COL}) 통계:")
        print(f"  Train  평균: {df_train_all[TARGET_COL].mean():.2f}  "
              f"std: {df_train_all[TARGET_COL].std():.2f}  "
              f"범위: {df_train_all[TARGET_COL].min():.2f}~{df_train_all[TARGET_COL].max():.2f}")
        print(f"  Test   평균: {df_test[TARGET_COL].mean():.2f}  "
              f"std: {df_test[TARGET_COL].std():.2f}  "
              f"범위: {df_test[TARGET_COL].min():.2f}~{df_test[TARGET_COL].max():.2f}")

        # numeric 변환 (비숫자 → NaN)
        df_train_all = df_train_all.apply(pd.to_numeric, errors='coerce')
        df_test      = df_test.apply(pd.to_numeric, errors='coerce')

        # 100% 결측 컬럼 제거
        drop_cols = df_train_all.columns[df_train_all.isnull().all()].tolist()
        if drop_cols:
            print(f"\n  100% 결측 컬럼 제거: {drop_cols}")
            df_train_all = df_train_all.drop(columns=drop_cols)
            df_test      = df_test.drop(columns=drop_cols, errors='ignore')

        # 공통 피처만 사용
        feat_cols = [c for c in df_train_all.columns if c != TARGET_COL]
        common_feats = [c for c in feat_cols if c in df_test.columns]

        # 결측치 제거 (numeric 변환 후)
        df_train_all = df_train_all.dropna(subset=common_feats + [TARGET_COL])
        df_test      = df_test.dropna(subset=common_feats + [TARGET_COL])
        print(f"  dropna 후 - Train: {len(df_train_all):,}행 / Test: {len(df_test):,}행")

        X_all  = df_train_all[common_feats].values
        y_all  = df_train_all[TARGET_COL].values
        X_test = df_test[common_feats].values
        y_test = df_test[TARGET_COL].values

        # 시계열 순서대로 train/val 분할 (80/20)
        split = int(len(X_all) * 0.8)
        X_train, X_val = X_all[:split], X_all[split:]
        y_train, y_val = y_all[:split], y_all[split:]

        print(f"\n📊 데이터 분할:")
        print(f"  Train: {len(X_train):,}행")
        print(f"  Val:   {len(X_val):,}행")
        print(f"  Test:  {len(X_test):,}행")
        print(f"  피처:  {len(common_feats)}개")

        return X_train, X_val, X_test, y_train, y_val, y_test, common_feats

    def train_ridge(self, X_train, X_val, X_test, y_train, y_val, y_test):
        print("\n" + "-"*70)
        print("🎯 모델: Ridge Regression")
        print("-"*70)

        start = time.time()
        model = Ridge(alpha=1.0)
        model.fit(X_train, y_train)
        elapsed = time.time() - start

        self._evaluate(
            'Ridge_RealData',
            (y_train, model.predict(X_train)),
            (y_val,   model.predict(X_val)),
            (y_test,  model.predict(X_test)),
            elapsed,
        )

    def train_lightgbm(self, X_train, X_val, X_test, y_train, y_val, y_test):
        print("\n" + "-"*70)
        print("🎯 모델: LightGBM")
        print("-"*70)

        import lightgbm as lgb

        start = time.time()
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data   = lgb.Dataset(X_val,   label=y_val, reference=train_data)

        params = {
            'learning_rate': 0.05,
            'num_leaves': 31,
            'max_depth': -1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'lambda_l2': 0.1,
            'objective': 'regression',
            'metric': 'mae',
            'verbose': -1,
        }

        model = lgb.train(
            params, train_data,
            num_boost_round=300,
            valid_sets=[train_data, val_data],
            callbacks=[lgb.early_stopping(30), lgb.log_evaluation(period=0)],
        )
        elapsed = time.time() - start

        self._evaluate(
            'LightGBM_RealData',
            (y_train, model.predict(X_train)),
            (y_val,   model.predict(X_val)),
            (y_test,  model.predict(X_test)),
            elapsed,
        )

    def train_xgboost(self, X_train, X_val, X_test, y_train, y_val, y_test):
        print("\n" + "-"*70)
        print("🎯 모델: XGBoost")
        print("-"*70)

        try:
            import xgboost as xgb
        except ImportError:
            print("❌ XGBoost not installed")
            return

        start = time.time()
        model = xgb.XGBRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=0,
            n_jobs=-1,
        )
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        elapsed = time.time() - start

        self._evaluate(
            'XGBoost_RealData',
            (y_train, model.predict(X_train)),
            (y_val,   model.predict(X_val)),
            (y_test,  model.predict(X_test)),
            elapsed,
        )

    def _evaluate(self, model_name, y_train, y_val, y_test, train_time):
        def metrics(y_true, y_pred):
            return {
                'mae':  mean_absolute_error(y_true, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            }

        m_train = metrics(*y_train)
        m_val   = metrics(*y_val)
        m_test  = metrics(*y_test)

        print(f"  ⏱️ 학습 시간: {train_time:.2f}초")
        print(f"  📊 Train MAE: {m_train['mae']:.6f}")
        print(f"  📊 Val   MAE: {m_val['mae']:.6f}")
        print(f"  🎯 Test  MAE: {m_test['mae']:.6f}")

        exp_id = f"exp_{self.exp_counter:03d}_{model_name.lower()}"
        self.exp_counter += 1

        metadata = {
            'experiment_id': exp_id,
            'model': model_name,
            'timestamp': datetime.now().isoformat(),
            'training_time_seconds': train_time,
            'performance': {
                'train_mae':  m_train['mae'],  'train_rmse': m_train['rmse'],
                'val_mae':    m_val['mae'],    'val_rmse':   m_val['rmse'],
                'test_mae':   m_test['mae'],   'test_rmse':  m_test['rmse'],
            },
            'data_type': 'real_data',
        }

        meta_path = self.metadata_dir / f"{exp_id}.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.results.append({
            'Exp_ID': exp_id,
            'Model': model_name,
            'Train_MAE': m_train['mae'],
            'Val_MAE':   m_val['mae'],
            'Test_MAE':  m_test['mae'],
            'Test_RMSE': m_test['rmse'],
            'Training_Time_sec': train_time,
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
        print(f"  ✅ 저장: {meta_path}")

    def run(self):
        print("\n🚀 실제 데이터로 모델 학습 시작")
        print("="*70)

        data = self.load_data()
        if data is None:
            return

        X_train, X_val, X_test, y_train, y_val, y_test, _ = data

        for train_func, name in [
            (self.train_ridge,    "Ridge"),
            (self.train_lightgbm, "LightGBM"),
            (self.train_xgboost,  "XGBoost"),
        ]:
            try:
                train_func(X_train, X_val, X_test, y_train, y_val, y_test)
            except Exception as e:
                print(f"❌ {name} 오류: {e}")

        self._save_results()

    def _save_results(self):
        print("\n" + "="*70)
        print("📋 실제 데이터 실험 결과")
        print("="*70)

        df_results = pd.DataFrame(self.results)
        summary_path = self.experiments_dir / 'results_summary.csv'

        if summary_path.exists():
            df_all = pd.concat([pd.read_csv(summary_path), df_results], ignore_index=True)
        else:
            df_all = df_results

        df_all.to_csv(summary_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ 결과 저장: {summary_path}\n")
        print(df_results.to_string(index=False))

        if len(df_results) > 0:
            best = df_results.iloc[df_results['Test_MAE'].idxmin()]
            print(f"\n🏆 최고 성능 모델:")
            print(f"   모델: {best['Model']}")
            print(f"   Test MAE: {best['Test_MAE']:.6f}")
            print(f"   학습 시간: {best['Training_Time_sec']:.2f}초")


if __name__ == '__main__':
    pipeline = RealDataMLPipeline()
    pipeline.run()
