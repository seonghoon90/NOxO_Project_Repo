#!/usr/bin/env python3
"""
실제 데이터 기반 Optuna 하이퍼파라미터 튜닝
- LightGBM / XGBoost / Ridge
- 오버피팅 방지 (정규화 강화)
"""

import time
import json
import warnings
import numpy as np
import pandas as pd
import optuna
from pathlib import Path
from datetime import datetime
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.linear_model import Ridge

warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)

DATA_DIR   = Path('/Users/gimhuitae/공모전/NOxO/data')
TRAIN_FILE = DATA_DIR / 'NOx_train_20250811_20250824.csv'
TEST_FILE  = DATA_DIR / 'NOx_test_20250825.csv'
TARGET_COL = 'IGCC.DeNOX.AT_H1_901_PV'
META_ROWS  = [1, 2, 3, 4]
N_TRIALS   = 60


def load_data():
    def read(path):
        df = pd.read_csv(path, skiprows=META_ROWS, encoding='utf-8-sig', low_memory=False)
        df = df.drop(columns=['TagName', 'Column1'], errors='ignore')
        return df.apply(pd.to_numeric, errors='coerce')

    print("📥 데이터 로드 중...")
    df_train_all = read(TRAIN_FILE)
    df_test      = read(TEST_FILE)

    # 100% 결측 컬럼 제거
    drop_cols = df_train_all.columns[df_train_all.isnull().all()].tolist()
    if drop_cols:
        df_train_all = df_train_all.drop(columns=drop_cols)
        df_test      = df_test.drop(columns=drop_cols, errors='ignore')

    feat_cols    = [c for c in df_train_all.columns if c != TARGET_COL]
    common_feats = [c for c in feat_cols if c in df_test.columns]

    df_train_all = df_train_all.dropna(subset=common_feats + [TARGET_COL])
    df_test      = df_test.dropna(subset=common_feats + [TARGET_COL])

    X_all  = df_train_all[common_feats].values
    y_all  = df_train_all[TARGET_COL].values
    X_test = df_test[common_feats].values
    y_test = df_test[TARGET_COL].values

    split = int(len(X_all) * 0.8)
    X_train, X_val = X_all[:split], X_all[split:]
    y_train, y_val = y_all[:split], y_all[split:]

    print(f"  Train: {len(X_train):,}  Val: {len(X_val):,}  Test: {len(X_test):,}  피처: {len(common_feats)}")
    return X_train, X_val, X_test, y_train, y_val, y_test


def tune_lightgbm(X_train, X_val, X_test, y_train, y_val, y_test):
    import lightgbm as lgb

    train_data = lgb.Dataset(X_train, label=y_train)
    val_data   = lgb.Dataset(X_val,   label=y_val, reference=train_data)

    def objective(trial):
        params = {
            'learning_rate':    trial.suggest_float('learning_rate', 0.01, 0.15, log=True),
            'num_leaves':       trial.suggest_int('num_leaves', 15, 127),
            'max_depth':        trial.suggest_int('max_depth', 3, 10),
            'min_child_samples':trial.suggest_int('min_child_samples', 20, 300),
            'subsample':        trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'lambda_l1':        trial.suggest_float('lambda_l1', 1e-4, 10.0, log=True),
            'lambda_l2':        trial.suggest_float('lambda_l2', 1e-4, 10.0, log=True),
            'feature_pre_filter': False,
            'objective': 'regression',
            'metric': 'mae',
            'verbose': -1,
        }
        model = lgb.train(
            params, train_data,
            num_boost_round=500,
            valid_sets=[val_data],
            callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(period=0)],
        )
        return mean_absolute_error(y_val, model.predict(X_val))

    print(f"\n🔍 LightGBM Optuna 튜닝 ({N_TRIALS}회)...")
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)

    best = study.best_params
    print(f"  Best Val MAE: {study.best_value:.6f}")
    print(f"  Best params: {best}")

    # 최적 파라미터로 최종 학습
    best['objective'] = 'regression'
    best['metric']    = 'mae'
    best['verbose']   = -1

    start = time.time()
    final_model = lgb.train(
        best, train_data,
        num_boost_round=500,
        valid_sets=[val_data],
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(period=0)],
    )
    elapsed = time.time() - start

    return final_model, elapsed, best, study.best_value


def tune_xgboost(X_train, X_val, X_test, y_train, y_val, y_test):
    import xgboost as xgb

    def objective(trial):
        params = dict(
            n_estimators      = 500,
            learning_rate     = trial.suggest_float('learning_rate', 0.01, 0.15, log=True),
            max_depth         = trial.suggest_int('max_depth', 3, 8),
            subsample         = trial.suggest_float('subsample', 0.5, 1.0),
            colsample_bytree  = trial.suggest_float('colsample_bytree', 0.5, 1.0),
            reg_alpha         = trial.suggest_float('reg_alpha', 1e-4, 10.0, log=True),
            reg_lambda        = trial.suggest_float('reg_lambda', 1e-4, 10.0, log=True),
            min_child_weight  = trial.suggest_int('min_child_weight', 1, 20),
            gamma             = trial.suggest_float('gamma', 0.0, 1.0),
            random_state      = 42,
            verbosity         = 0,
            n_jobs            = -1,
        )
        model = xgb.XGBRegressor(**params)
        model.fit(X_train, y_train,
                  eval_set=[(X_val, y_val)],
                  verbose=False)
        return mean_absolute_error(y_val, model.predict(X_val))

    print(f"\n🔍 XGBoost Optuna 튜닝 ({N_TRIALS}회)...")
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)

    best = study.best_params
    print(f"  Best Val MAE: {study.best_value:.6f}")
    print(f"  Best params: {best}")

    start = time.time()
    final_model = xgb.XGBRegressor(
        **best,
        n_estimators=500,
        random_state=42,
        verbosity=0,
        n_jobs=-1,
    )
    final_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    elapsed = time.time() - start

    return final_model, elapsed, best, study.best_value


def tune_ridge(X_train, X_val, X_test, y_train, y_val, y_test):
    def objective(trial):
        alpha = trial.suggest_float('alpha', 1e-3, 1e4, log=True)
        model = Ridge(alpha=alpha)
        model.fit(X_train, y_train)
        return mean_absolute_error(y_val, model.predict(X_val))

    print(f"\n🔍 Ridge Optuna 튜닝 ({N_TRIALS}회)...")
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)

    best = study.best_params
    print(f"  Best Val MAE: {study.best_value:.6f}")
    print(f"  Best params: {best}")

    start = time.time()
    final_model = Ridge(alpha=best['alpha'])
    final_model.fit(X_train, y_train)
    elapsed = time.time() - start

    return final_model, elapsed, best, study.best_value


def evaluate_and_save(model_name, model, X_train, X_val, X_test,
                      y_train, y_val, y_test, elapsed, best_params,
                      results_dir, exp_counter):
    pred_fn = model.predict

    metrics = {
        'train_mae':  mean_absolute_error(y_train, pred_fn(X_train)),
        'train_rmse': np.sqrt(mean_squared_error(y_train, pred_fn(X_train))),
        'val_mae':    mean_absolute_error(y_val,   pred_fn(X_val)),
        'val_rmse':   np.sqrt(mean_squared_error(y_val,   pred_fn(X_val))),
        'test_mae':   mean_absolute_error(y_test,  pred_fn(X_test)),
        'test_rmse':  np.sqrt(mean_squared_error(y_test,  pred_fn(X_test))),
    }

    print(f"\n  📊 Train MAE: {metrics['train_mae']:.6f}")
    print(f"  📊 Val   MAE: {metrics['val_mae']:.6f}")
    print(f"  🎯 Test  MAE: {metrics['test_mae']:.6f}")
    print(f"  ⏱️ 학습 시간: {elapsed:.2f}초")

    meta_dir = results_dir / 'metadata'
    meta_dir.mkdir(parents=True, exist_ok=True)
    exp_id = f"exp_{exp_counter:03d}_{model_name.lower()}_optuna"

    with open(meta_dir / f"{exp_id}.json", 'w', encoding='utf-8') as f:
        json.dump({
            'experiment_id': exp_id,
            'model': model_name,
            'timestamp': datetime.now().isoformat(),
            'training_time_seconds': elapsed,
            'performance': metrics,
            'best_params': best_params,
            'data_type': 'real_data_optuna',
        }, f, indent=2, ensure_ascii=False)

    return {
        'Exp_ID': exp_id, 'Model': model_name,
        'Train_MAE': metrics['train_mae'], 'Val_MAE': metrics['val_mae'],
        'Test_MAE': metrics['test_mae'],   'Test_RMSE': metrics['test_rmse'],
        'Training_Time_sec': elapsed,
        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }


def main():
    print("\n🚀 Optuna 하이퍼파라미터 튜닝 시작")
    print("="*70)

    X_train, X_val, X_test, y_train, y_val, y_test = load_data()

    experiments_dir = Path('experiments')
    exp_counter = len(list((experiments_dir / 'metadata').glob('exp_*.json'))) + 1

    results = []

    tasks = [
        ('LightGBM', tune_lightgbm),
    ]

    for name, tune_fn in tasks:
        print(f"\n{'='*70}")
        print(f"🎯 {name} 튜닝")
        print('='*70)
        try:
            model, elapsed, best_params, _ = tune_fn(
                X_train, X_val, X_test, y_train, y_val, y_test
            )
            row = evaluate_and_save(
                name, model,
                X_train, X_val, X_test,
                y_train, y_val, y_test,
                elapsed, best_params,
                experiments_dir, exp_counter,
            )
            results.append(row)
            exp_counter += 1
        except Exception as e:
            print(f"❌ {name} 오류: {e}")
            import traceback; traceback.print_exc()

    # 결과 저장
    print("\n" + "="*70)
    print("📋 Optuna 튜닝 결과")
    print("="*70)

    df_results = pd.DataFrame(results)
    summary_path = experiments_dir / 'results_summary.csv'
    if summary_path.exists():
        df_all = pd.concat([pd.read_csv(summary_path), df_results], ignore_index=True)
    else:
        df_all = df_results
    df_all.to_csv(summary_path, index=False, encoding='utf-8-sig')

    print(f"\n✅ 결과 저장: {summary_path}\n")
    print(df_results.to_string(index=False))

    if len(df_results) > 0:
        best = df_results.iloc[df_results['Test_MAE'].idxmin()]
        print(f"\n🏆 최고 성능 (Optuna 튜닝):")
        print(f"   모델:      {best['Model']}")
        print(f"   Test MAE:  {best['Test_MAE']:.6f}")
        print(f"   Val MAE:   {best['Val_MAE']:.6f}")
        print(f"   학습 시간: {best['Training_Time_sec']:.2f}초")


if __name__ == '__main__':
    main()
