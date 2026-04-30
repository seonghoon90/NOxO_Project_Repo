# 하이퍼파라미터 튜닝 가이드

> **목적**: Baseline 모델을 넘는 최고 성능 모델을 찾기 위한 체계적 튜닝 전략
> **작성일**: 2026-04-30

---

## 📚 기본 개념

### 하이퍼파라미터 vs 파라미터
| 구분 | 정의 | 예시 |
|------|------|------|
| **파라미터** | 데이터에서 학습됨 | 가중치(weights) |
| **하이퍼파라미터** | 사람이 설정해야 함 | Learning rate, Tree depth |

### 왜 튜닝이 필요한가?
```
기본값만 사용: MAE = 0.092
튜닝 후:      MAE = 0.085  (+7.6% 개선)
```

---

## 🎯 튜닝 전략: 단계별 접근

### 단계 1: 기본값으로 "빠른 실험" (1시간)

**목표**: 모델이 제대로 작동하는지 확인

```yaml
# configs/exp_lightgbm_baseline.yaml
lightgbm:
  n_estimators: 100          # 빠른 확인용 (나중에 500으로)
  learning_rate: 0.1         # 기본값
  num_leaves: 31             # 기본값
  max_depth: -1
  subsample: 1.0
  colsample_bytree: 1.0
  lambda_l1: 0.0
  lambda_l2: 0.0
  min_child_samples: 20
```

**결과 기록**:
```json
{
  "experiment_id": "exp_001_lightgbm_baseline",
  "val_mae": 0.0920,
  "val_rmse": 0.1160,
  "train_time_sec": 45
}
```

### 단계 2: 정규화 튜닝 (과적합 방지)

**목표**: 과적합을 줄이면서 성능 개선

#### 2-1. Learning Rate 조정
```python
# learning_rate를 작게 → 더 정교한 학습 (대신 느려짐)

learning_rates = [0.001, 0.005, 0.01, 0.05, 0.1]

for lr in learning_rates:
    model = lgb.train(
        params={'learning_rate': lr, 'n_estimators': 500, ...},
        train_data, ...
    )
    val_mae = evaluate(model, X_val, y_val)
    print(f"LR={lr}: MAE={val_mae:.4f}")

# 결과 예상:
# LR=0.001: MAE=0.0912 (느리지만 안정적)
# LR=0.01:  MAE=0.0908 ← 최고
# LR=0.1:   MAE=0.0920 (빠르지만 거칠음)
```

#### 2-2. Tree Depth 조정
```python
# num_leaves가 작을수록 정규화 강함

num_leaves_list = [7, 15, 31, 63, 127]

for num_leaves in num_leaves_list:
    model = lgb.train(
        params={'num_leaves': num_leaves, 'learning_rate': 0.01, ...},
        train_data, ...
    )
    val_mae = evaluate(model, X_val, y_val)
    print(f"Leaves={num_leaves}: MAE={val_mae:.4f}")

# 결과 예상:
# Leaves=7:   MAE=0.0918 (과소 적합)
# Leaves=15:  MAE=0.0906 ← 최고
# Leaves=31:  MAE=0.0908
# Leaves=63:  MAE=0.0912 (과적합)
# Leaves=127: MAE=0.0915 (과적합)
```

#### 2-3. Regularization (L1, L2, Subsample)
```python
# L2 정규화 강도 테스트
lambda_l2_list = [0.0, 0.1, 1.0, 10.0, 100.0]

for lambda_l2 in lambda_l2_list:
    model = lgb.train(
        params={
            'learning_rate': 0.01,
            'num_leaves': 15,
            'lambda_l2': lambda_l2,
            ...
        },
        train_data, ...
    )
    val_mae = evaluate(model, X_val, y_val)
    print(f"L2={lambda_l2}: MAE={val_mae:.4f}")

# 결과 예상:
# L2=0.0:   MAE=0.0906
# L2=0.1:   MAE=0.0904 ← 최고
# L2=1.0:   MAE=0.0907
# L2=10.0:  MAE=0.0912 (과다 정규화)
```

### 단계 3: 자동화된 튜닝 (Optuna)

**목표**: 위의 모든 파라미터를 한 번에 최적화

#### 3-1. Optuna 설치
```bash
pip install optuna
```

#### 3-2. 튜닝 코드
```python
import optuna
from optuna.samplers import TPESampler
import lightgbm as lgb

def objective(trial):
    """최적화할 목적함수 (validation MAE를 최소화)"""
    
    # 튜닝할 파라미터 범위 정의
    params = {
        'learning_rate': trial.suggest_loguniform('learning_rate', 0.001, 0.1),
        'num_leaves': trial.suggest_int('num_leaves', 7, 127),
        'max_depth': trial.suggest_int('max_depth', 3, 20),
        'lambda_l1': trial.suggest_loguniform('lambda_l1', 1e-5, 1.0),
        'lambda_l2': trial.suggest_loguniform('lambda_l2', 1e-5, 1.0),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),
    }
    
    # 모델 학습
    model = lgb.train(
        params,
        train_data,
        num_boost_round=500,
        valid_sets=[val_data],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)],
    )
    
    # Validation 성능 반환
    val_pred = model.predict(X_val)
    val_mae = mean_absolute_error(y_val, val_pred)
    
    return val_mae

# 튜닝 실행
sampler = TPESampler(seed=42)
study = optuna.create_study(
    sampler=sampler,
    direction='minimize',  # MAE 최소화
)

study.optimize(
    objective,
    n_trials=50,  # 50번의 시행 (대략 2-4시간)
    n_jobs=-1,    # 병렬 처리 (CPU 모든 코어 사용)
)

# 최고 파라미터 출력
print("✅ Best hyperparameters:")
print(study.best_params)
print(f"Best validation MAE: {study.best_value:.4f}")

# 최고 파라미터로 최종 모델 학습
best_params = study.best_params
final_model = lgb.train(best_params, train_data, num_boost_round=500, ...)
```

#### 3-3. Optuna 결과 분석
```python
# 튜닝 히스토리 시각화
import matplotlib.pyplot as plt

# 1. Optimization history
trials_df = study.trials_dataframe()
plt.figure(figsize=(10, 6))
plt.plot(trials_df['number'], trials_df['value'])
plt.xlabel('Trial')
plt.ylabel('Validation MAE')
plt.title('Optuna Optimization Progress')
plt.grid()
plt.savefig('reports/optuna_history.png', dpi=150, bbox_inches='tight')

# 2. Parameter importance
importance = optuna.visualization.plot_param_importances(study)
importance.write_html('reports/optuna_param_importance.html')

# 3. 최고 N개 시행 비교
best_10 = trials_df.nsmallest(10, 'value')
print(best_10[['number', 'value', 'params_learning_rate', 'params_num_leaves']])
```

---

## 🔄 실제 워크플로우

### Week 4: 하이퍼파라미터 튜닝

#### Day 1: 준비 & 빠른 실험
```bash
# 1. 최고 모델(예: LightGBM) 선택
# 2. 기본 설정으로 빠른 실험 실행
python scripts/run_experiment.py --config configs/exp_lightgbm_baseline.yaml

# 결과: exp_003_lightgbm_v1 (Val MAE: 0.0912)
```

#### Day 2-4: 단계적 튜닝
```bash
# 1단계: Learning Rate 탐색
python scripts/hyperparameter_search.py --param learning_rate --values 0.001,0.005,0.01,0.05,0.1

# 결과: LR=0.01이 최고 (MAE 0.0908)

# 2단계: Num Leaves 탐색 (LR=0.01로 고정)
python scripts/hyperparameter_search.py --param num_leaves --lr 0.01 --values 7,15,31,63,127

# 결과: Leaves=15가 최고 (MAE 0.0906)

# 3단계: 정규화 파라미터 탐색 (LR=0.01, Leaves=15로 고정)
python scripts/hyperparameter_search.py --params lambda_l2,subsample --lr 0.01 --leaves 15
```

#### Day 5: Optuna 자동 튜닝
```bash
# 모든 파라미터를 동시에 최적화 (GPU 활용하면 빠름)
python scripts/optuna_tuning.py \
  --model_type lightgbm \
  --n_trials 50 \
  --n_jobs 4

# 약 2-4시간 소요
# 결과: exp_010_lightgbm_optuna_tuned (Val MAE: 0.0887)
```

---

## 📊 튜닝 결과 비교 템플릿

실험 완료 후 이런 표를 작성하세요:

```markdown
## 하이퍼파라미터 튜닝 결과

| 단계 | 모델 설정 | Val MAE | Test MAE | 개선도 | 비고 |
|------|---------|---------|---------|--------|------|
| 기본값 | LR=0.1, Leaves=31 | 0.0920 | 0.0988 | 0% | Baseline |
| LR 튜닝 | LR=0.01, Leaves=31 | 0.0908 | 0.0975 | +1.3% | 최적 LR 발견 |
| Leaves 튜닝 | LR=0.01, Leaves=15 | 0.0906 | 0.0972 | +1.5% | 과적합 감소 |
| L2 튜닝 | LR=0.01, Leaves=15, L2=0.1 | 0.0904 | 0.0970 | +1.7% | 정규화 강화 |
| **Optuna (50회)** | **모든 파라미터 최적화** | **0.0887** | **0.0955** | **+3.6%** | 🏆 최고 성능 |

**결론**: Optuna 자동 튜닝으로 Baseline 대비 3.6% 개선 달성. 
         Test 성능도 Baseline 대비 3.3% 개선으로 일반화 성능 입증.
```

---

## ⚠️ 튜닝할 때 주의사항

### 주의 1: 과도한 튜닝 (Overfitting to Validation Set)
```
❌ 나쁜 예:
- Validation Set을 너무 많이 보면서 튜닝
- 1000회 이상의 trial 실행
- 결과: Validation에서 좋지만 Test에서 나쁨

✅ 좋은 예:
- 50~100회 정도의 trial로 충분
- 최고 성능 모델의 Test 성능도 확인
- 최종 선택은 Test 성능 기반
```

### 주의 2: 시계열 데이터 특성 유지
```python
# ❌ 나쁜 예: shuffle=True (시간 순서 섞임)
X_train, X_val = train_test_split(X, test_size=0.2, shuffle=True)

# ✅ 좋은 예: shuffle=False (시간순 분할)
split_point = int(len(X) * 0.8)
X_train, X_val = X[:split_point], X[split_point:]
y_train, y_val = y[:split_point], y[split_point:]
```

### 주의 3: 빠른 실험과 최종 튜닝 구분
```
Phase 1 (빠른 실험, 1-2시간):
  - n_estimators = 100 (빠르게)
  - 기본 정규화만 사용
  - → 어떤 모델이 유망한지 판단

Phase 2 (최종 튜닝, 2-4시간):
  - n_estimators = 500 (충분히)
  - Optuna로 세밀한 튜닝
  - → 최고 성능 추출
```

---

## 💡 팁: 튜닝 효율성 높이기

### Tip 1: Learning Rate는 먼저
```
tuning 순서:
1. Learning Rate (가장 영향도 큼)
2. Tree Depth (두 번째로 중요)
3. Regularization (세 번째)
4. Subsample (세세한 조정)
```

### Tip 2: 병렬 처리 활용
```python
# GPU가 있으면 device='gpu' 추가
# CPU 코어가 여러 개면 n_jobs=-1로 병렬화

study.optimize(
    objective,
    n_trials=100,
    n_jobs=4,  # 4개 프로세스 병렬 실행
    show_progress_bar=True,
)
```

### Tip 3: 중간 저장
```python
# Optuna 결과를 계속 저장
study.optimize(objective, n_trials=25)
# ... 확인 ...
study.optimize(objective, n_trials=25)  # +25회 추가
# ... 확인 ...
study.optimize(objective, n_trials=25)  # 총 75회

# 언제든 최고 결과 확인 가능
```

---

## 🎓 Expected Improvement

### 베이스라인 → 튜닝 후 기대값

| 모델 | 기본값 MAE | 튜닝 후 MAE | 개선도 |
|------|----------|----------|--------|
| LightGBM | 0.0920 | 0.0885 | +3.8% |
| TabNet | 0.0925 | 0.0895 | +3.2% |
| XGBoost | 0.0920 | 0.0880 | +4.3% |

---

## ✅ 튜닝 체크리스트

- [ ] 단계 1: 기본값 실험 완료
- [ ] 단계 2: Learning Rate 튜닝 완료
- [ ] 단계 2: Num Leaves 튜닝 완료
- [ ] 단계 2: Regularization 튜닝 완료
- [ ] 단계 3: Optuna 자동 튜닝 실행 (50~100회)
- [ ] 최고 모델 선택
- [ ] Test Set 검증
- [ ] 튜닝 결과 보고서 작성
- [ ] 최종 모델 저장

---

**다음 단계**: 최종 모델 검증 & 배포 준비
