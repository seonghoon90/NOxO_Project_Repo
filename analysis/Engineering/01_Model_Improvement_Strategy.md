# 모델 개선 전략: 후보 모델 상세 가이드

> **목적**: Baseline (Ridge, XGBoost)을 넘을 수 있는 후보 모델들의 학습 전략
> **작성일**: 2026-04-30

---

## 개요: 후보 모델 5가지

| 순번 | 모델 | 추천도 | 이유 | 기대 성능 | 개발난도 |
|------|------|--------|------|---------|---------|
| 1 | **LightGBM** | ⭐⭐⭐⭐⭐ | XGBoost보다 빠르고 좋음 | Baseline 대비 +2~5% | 낮음 |
| 2 | **TabNet** | ⭐⭐⭐⭐ | 해석성 + 성능 | Baseline 대비 +1~3% | 중간 |
| 3 | **MLP (Neural Network)** | ⭐⭐⭐ | 깊은 비선형 학습 | Baseline 대비 ±2% | 높음 |
| 4 | **앙상블** | ⭐⭐⭐⭐ | 여러 모델 결합 | Baseline 대비 +3~6% | 낮음 |
| 5 | **Segment 모델** | ⭐⭐⭐⭐⭐ | 부하별 맞춤 | Baseline 대비 +2~4% | 중간 |

---

## 모델 1️⃣: LightGBM — 빠르고 우수한 성능

### 왜 시작해야 하나?
- XGBoost의 업그레이드판 (더 빠르고, 메모리 효율적)
- GPU 지원으로 대량 데이터에서도 빠름
- Feature importance 해석성 우수
- **추천**: 가장 먼저 시도할 모델

### 학습 전략

#### Step 1: 기본 하이퍼파라미터 설정
```yaml
# configs/exp_lightgbm_v1.yaml
model:
  type: LightGBM
  n_estimators: 500
  learning_rate: 0.05
  num_leaves: 31
  max_depth: -1
  min_child_samples: 20
  subsample: 0.8
  colsample_bytree: 0.8
  lambda_l1: 0.0
  lambda_l2: 0.1
  
train:
  early_stopping_rounds: 50
  valid_size: 0.2
  cv_folds: 5
```

#### Step 2: 학습 과정
```python
# scripts/train_model.py의 일부
import lightgbm as lgb
from sklearn.model_selection import train_test_split

# 데이터 로드
X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, shuffle=False  # 시계열이므로 shuffle=False!
)

# LightGBM 데이터셋 생성
train_data = lgb.Dataset(X_train, label=y_train)
val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

# 학습
model = lgb.train(
    params,
    train_data,
    num_boost_round=500,
    valid_sets=[train_data, val_data],
    callbacks=[lgb.early_stopping(50), lgb.log_evaluation()],
)
```

#### Step 3: 성능 평가
```python
# MAE, RMSE, MAPE 계산
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
mape = mean_absolute_percentage_error(y_test, y_pred)

print(f"Test MAE: {mae:.4f}")  # Baseline과 비교
```

### 예상 결과
- **성능**: Ridge보다 3~5%, XGBoost와 비슷하거나 조금 나음
- **학습 시간**: XGBoost의 50~70%
- **해석성**: Feature importance로 상위 10개 피처 확인 가능

### 주의사항
- ❌ Hyperparameter 튜닝에 너무 오래 소비하지 말 것 (이후 단계에서 최적화)
- ✅ Early stopping으로 과적합 방지
- ✅ Feature importance plot을 생성해서 어떤 피처가 중요한지 파악

---

## 모델 2️⃣: TabNet — 해석성이 있는 신경망

### 왜 시도해야 하나?
- Tree 모델보다 깊은 비선형 학습 가능
- 피처 선택이 투명함 (어떤 피처가 각 샘플별로 사용되었는지 확인 가능)
- GPU 가속 가능
- **추천**: LightGBM 다음으로 시도

### 학습 전략

#### Step 1: 환경 설정
```bash
pip install pytorch-tabnet
```

#### Step 2: 데이터 전처리 (TabNet의 특수성)
```python
# TabNet은 정규화가 중요
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)
```

#### Step 3: 모델 학습
```python
from pytorch_tabnet.tab_model import TabNetRegressor

model = TabNetRegressor(
    n_d=64,           # Decision step dimension
    n_a=64,           # Attention step dimension
    n_steps=5,        # Number of decision steps
    lambda_sparse=1e-5,
    optimizer_fn=torch.optim.Adam,
    optimizer_params={"lr": 1e-3},
    mask_type='sparsemax',
    verbose=1
)

model.fit(
    X_train_scaled, y_train,
    eval_set=[(X_val_scaled, y_val)],
    eval_metric=['rmse'],
    max_epochs=200,
    patience=20,
    batch_size=1024,
)
```

#### Step 4: 해석성 분석
```python
# TabNet은 피처별 사용 빈도를 추적
feature_importance = model.feature_importances_
feature_masks = model.feature_importances_

# 어떤 피처가 가장 자주 선택되었는가?
top_features = sorted(
    zip(feature_names, feature_importance),
    key=lambda x: x[1],
    reverse=True
)
```

### 예상 결과
- **성능**: Baseline 대비 1~3% 개선 가능
- **학습 시간**: LightGBM보다 느림 (GPU에서는 비슷)
- **해석성**: Tree보다 해석이 어렵지만, Mask를 통해 부분적 투명성 제공

### 주의사항
- ⚠️ 데이터 정규화 필수 (안 하면 성능이 매우 나쁨)
- ⚠️ 조기 종료(early stopping) 설정 필수
- ✅ GPU가 있으면 학습이 빠름

---

## 모델 3️⃣: Segment 모델 (부하별 맞춤)

### 왜 시도해야 하나?
- **HYP-2**: "부하 구간별 NOx 생성 양상 변화"에서 발견된 기회
- 저부하/중부하/고부하에서 다른 제어 전략이 적용됨
- 단일 모델보다 각 구간 특성에 맞춘 모델이 더 정확할 가능성
- **추천**: LightGBM과 동시에 병렬 진행

### 학습 전략

#### Step 1: 부하 구간 정의
```python
# DWATT(발전 출력) 기준으로 3개 구간 분할
# 과거 분석에서 어떻게 분할했는지 확인 필요

# 임시 정의 (도메인 전문가와 확인 후 수정)
low_load = df[df['DWATT'] < 20]      # 저부하
mid_load = df[(df['DWATT'] >= 20) & (df['DWATT'] < 35)]   # 중부하
high_load = df[df['DWATT'] >= 35]    # 고부하

print(f"Low: {len(low_load)}, Mid: {len(mid_load)}, High: {len(high_load)}")
```

#### Step 2: 각 구간별 모델 학습
```python
models = {}

for segment, data in [('low', low_load), ('mid', mid_load), ('high', high_load)]:
    X_seg = data[feature_cols]
    y_seg = data['target']
    
    # Temporal split (시계열 특성 유지)
    split_point = int(len(X_seg) * 0.8)
    X_train, X_val = X_seg[:split_point], X_seg[split_point:]
    y_train, y_val = y_seg[:split_point], y_seg[split_point:]
    
    # LightGBM 학습
    model = lgb.train(params, lgb.Dataset(X_train, label=y_train), ...)
    models[segment] = model
    
    # 성능 평가
    pred = model.predict(X_val)
    mae = mean_absolute_error(y_val, pred)
    print(f"{segment.upper()} segment MAE: {mae:.4f}")
```

#### Step 3: 예측 (추론)
```python
def predict_segment(X_test):
    """부하에 따라 적절한 모델 선택해서 예측"""
    predictions = np.zeros(len(X_test))
    
    for segment, threshold in [
        ('low', 20),
        ('mid', 35),
        ('high', np.inf)
    ]:
        if segment == 'low':
            mask = X_test['DWATT'] < threshold
        elif segment == 'mid':
            mask = (X_test['DWATT'] >= 20) & (X_test['DWATT'] < threshold)
        else:
            mask = X_test['DWATT'] >= 35
        
        if mask.any():
            pred = models[segment].predict(X_test[mask])
            predictions[mask] = pred
    
    return predictions
```

### 예상 결과
- **성능**: Segment 모델 3개 가중합 vs Global 모델 1개 (5~10% 개선 기대)
- **복잡도**: 3개 모델 관리 필요 (배포 시 추론 로직 복잡)
- **장점**: 각 구간에 특화된 모델로 정확도 향상

### 주의사항
- ⚠️ 각 구간별 데이터 부족 시 과적합 위험
- ⚠️ 구간 경계(20, 35)에서 예측 불안정성 가능
- ✅ 경계 근처에서 두 모델 평균으로 부드러운 전환 고려

---

## 모델 4️⃣: 앙상블 (모델 결합)

### 왜 시도해야 하나?
- 여러 모델의 장점을 결합하면 더 나은 성능 가능
- Random Forest처럼 배깅 방식으로 분산 줄임
- **추천**: LightGBM, TabNet, Segment 모델 완성 후 진행

### 학습 전략

#### Step 1: 가중 평균 앙상블 (가장 간단)
```python
# 각 모델이 학습 완료된 상태
pred_lgb = lgb_model.predict(X_test)
pred_tabnet = tabnet_model.predict(X_test)
pred_segment = predict_segment(X_test)

# 가중 평균 (가중치는 검증셋 성능 기반)
weights = [0.4, 0.3, 0.3]  # LightGBM, TabNet, Segment
ensemble_pred = (
    weights[0] * pred_lgb +
    weights[1] * pred_tabnet +
    weights[2] * pred_segment
)
```

#### Step 2: Stacking 앙상블 (고급)
```python
# Base 모델들의 검증셋 예측을 메타-모델의 입력으로 사용
from sklearn.ensemble import VotingRegressor

ensemble = VotingRegressor(
    estimators=[
        ('lgb', lgb_model),
        ('tabnet', tabnet_model),
        # ('segment', segment_ensemble),  # 직접 포함 어려움
    ],
    weights=[0.4, 0.3],
)

ensemble.fit(X_train, y_train)
pred = ensemble.predict(X_test)
```

### 예상 결과
- **성능**: 최고 모델보다 2~5% 추가 개선
- **안정성**: 단일 모델보다 분산 감소

---

## 모델 5️⃣: MLP (신경망)

### 왜 시도해야 하나?
- 가장 깊은 비선형 학습 가능
- 충분한 데이터(1.3M 샘플)가 있으므로 신경망 적합
- 최신 기술 시도 기회
- **추천**: 다른 모델들이 어느 정도 수렴한 후 (시간이 충분하면)

### 학습 전략

```python
import tensorflow as tf
from tensorflow.keras import layers, models

# 모델 구축
model = models.Sequential([
    layers.Dense(256, activation='relu', input_dim=n_features),
    layers.BatchNormalization(),
    layers.Dropout(0.3),
    
    layers.Dense(128, activation='relu'),
    layers.BatchNormalization(),
    layers.Dropout(0.3),
    
    layers.Dense(64, activation='relu'),
    layers.BatchNormalization(),
    layers.Dropout(0.2),
    
    layers.Dense(32, activation='relu'),
    layers.Dense(1)  # Regression output
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss='mse',
    metrics=['mae']
)

# 학습
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=100,
    batch_size=512,
    callbacks=[
        tf.keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True),
    ]
)
```

### 주의사항
- ⚠️ 하이퍼파라미터 튜닝 매우 어려움 (학습률, 층 깊이, 드롭아웃 등)
- ⚠️ 해석성 낮음 (검은 상자)
- ⚠️ 데이터 정규화 필수
- ✅ 검증 곡선 모니터링으로 과적합 감지

---

## 📊 모델 비교 표 (완성 후)

실험 완료 후 다음과 같은 표를 작성하세요:

| 모델 | Test MAE | Test RMSE | 학습시간 | 해석성 | 복잡도 |
|------|----------|-----------|---------|--------|--------|
| Ridge (Baseline) | 0.095 | 0.121 | 빠름 | 높음 | 낮음 |
| XGBoost (Baseline) | 0.089 | 0.115 | 중간 | 중간 | 중간 |
| **LightGBM** | ? | ? | ? | ? | ? |
| **TabNet** | ? | ? | ? | ? | ? |
| **Segment** | ? | ? | ? | ? | ? |
| **Ensemble** | ? | ? | ? | ? | ? |
| MLP | ? | ? | ? | ? | ? |

---

## 🎯 실험 순서 추천

```
Week 2 (병렬 진행):
  ├─ Day 1-2: LightGBM (가장 유망)
  └─ Day 1-3: Segment 모델 (도메인 검증 필요)

Week 3:
  ├─ Day 1-2: TabNet (LightGBM 완성 후)
  └─ Day 3-5: Ensemble (각 모델 완성 후)

Week 4 (시간 남으면):
  └─ MLP 시도
```

---

**다음 문서**: `02_Experiment_Tracking.md` (실험 기록 관리)
