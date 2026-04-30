# NOx 예측 AI 엔지니어링 프로젝트

> **프로젝트**: IGCC 가스터빈 배기 NOx 예측 AI 모델 최적화
> **기반**: `../nox_manual_baseline/` (Stage 00P~07 완료)
> **목표**: Ridge/XGBoost Baseline을 넘는 최고 성능 모델 개발
> **예상 기간**: 5주

---

## 🎯 목표 & KPI

### Primary Goal
Baseline 성능 대비 **5% 이상 개선**한 프로덕션 모델 개발

| 모델 | Test MAE | Target | 상태 |
|------|----------|--------|------|
| Ridge (Baseline) | 0.0950 | - | ✅ 완료 |
| XGBoost (Baseline) | 0.0891 | - | ✅ 완료 |
| **목표 모델** | **0.0845** | -5% | 🔄 진행중 |

### Success Criteria
- [ ] Test MAE < 0.0845 (5% 개선)
- [ ] Validation에서 과적합 없음 (Train-Val gap < 1%)
- [ ] 모델 해석 가능 (Feature importance 분석)
- [ ] 배포 가능한 상태 (ONNX, inference 코드)

---

## 📋 실행 로드맵

### Week 1: 베이스라인 재현 & 이해
```
□ Stage 05~07 코드 분석
□ Ridge/XGBoost 모델 재현
□ 성능 지표 기록
□ 데이터셋 구조 이해
```

**산출물**: `reports/baseline_reproduction.md`

### Week 2-3: 모델 개선 실험
```
□ LightGBM 학습
□ TabNet 학습
□ Segment 모델 (부하별) 학습
□ 앙상블 모델 구성
□ Top 3 모델 선정
```

**산출물**: `reports/model_improvement_experiments.md`

### Week 4: 하이퍼파라미터 튜닝
```
□ 최고 모델 선택
□ Optuna로 50~100회 튜닝
□ 튜닝 전/후 성능 비교
□ 최종 모델 확정
```

**산출물**: `reports/hyperparameter_tuning.md`, `models/production_model_v1.pkl`

### Week 5: 검증 & 배포 준비
```
□ Test Set 최종 검증
□ SHAP 해석성 분석
□ 에러 분석 & 개선점 도출
□ 배포용 패키지 준비
```

**산출물**: `reports/final_model_validation.md`, inference 파이프라인

---

## 📁 폴더 구조

```
analysis/Engineering/
├── README.md (이 파일)
│
├── 00_AI_Engineering_Guide.md         ← 시작: 전체 가이드
├── 01_Model_Improvement_Strategy.md   (5개 후보 모델 상세)
├── 02_Experiment_Tracking.md          (실험 추적 방법)
├── 03_Hyperparameter_Tuning.md        (튜닝 전략)
│
├── configs/                           (모델 설정)
│   ├── baseline_ridge.yaml
│   ├── baseline_xgboost.yaml
│   ├── exp_lightgbm_v1.yaml
│   ├── exp_tabnet_v1.yaml
│   └── exp_neural_network_v1.yaml
│
├── scripts/                           (실행 스크립트)
│   ├── run_experiment.py              (통합 실험 실행)
│   ├── preprocess.py                  (데이터 전처리)
│   ├── train_model.py                 (모델 학습)
│   ├── evaluate.py                    (평가 & 분석)
│   ├── hyperparameter_search.py       (단계적 튜닝)
│   ├── optuna_tuning.py               (자동 튜닝)
│   ├── shap_analysis.py               (해석성 분석)
│   └── inference.py                   (추론 파이프라인)
│
├── experiments/                       (실험 결과)
│   ├── metadata/                      (JSON 메타데이터)
│   │   ├── exp_001_ridge_baseline.json
│   │   ├── exp_002_xgboost_baseline.json
│   │   ├── exp_003_lightgbm_v1.json
│   │   └── ...
│   ├── models/                        (학습된 모델)
│   │   ├── exp_001_model.pkl
│   │   ├── exp_002_model.pkl
│   │   └── ...
│   ├── logs/                          (학습 로그)
│   └── results_summary.csv            (자동 생성 비교표)
│
├── models/                            (최종 모델)
│   ├── production_model_v1.pkl        (최고 성능 모델)
│   ├── production_model_v1.onnx       (배포용)
│   └── model_metadata.json
│
└── reports/                           (분석 보고서)
    ├── baseline_reproduction.md
    ├── model_improvement_experiments.md
    ├── hyperparameter_tuning.md
    ├── final_model_validation.md
    └── figures/
        ├── shap_importance.png
        ├── residual_analysis.png
        ├── performance_comparison.png
        └── ...
```

---

## 🚀 빠른 시작

### 1️⃣ 환경 설정

```bash
# 로컬 가상환경 생성
python3 -m venv .venv
source .venv/bin/activate

# 필요한 패키지 설치
python -m pip install pyarrow lightgbm xgboost tabnet optuna pandas scikit-learn pyyaml joblib

# (선택) GPU 지원
python -m pip install lightgbm[gpu] xgboost[gpu]
```

`pyarrow`가 없으면 `synthetic_data.parquet`와 baseline parquet 파일을 읽지 못해
실험 스크립트가 시작 단계에서 실패한다.

### 2️⃣ 베이스라인 재현 (Week 1)

```bash
# Ridge 베이스라인 실행
python scripts/run_experiment.py --config configs/baseline_ridge.yaml

# XGBoost 베이스라인 실행
python scripts/run_experiment.py --config configs/baseline_xgboost.yaml

# 결과 확인
cat experiments/results_summary.csv
```

### 3️⃣ LightGBM 실험 (Week 2)

```bash
# LightGBM v1 실행
python scripts/run_experiment.py --config configs/exp_lightgbm_v1.yaml

# 결과 분석
python scripts/evaluate.py --exp exp_003_lightgbm_v1 --plot
```

### 4️⃣ 하이퍼파라미터 튜닝 (Week 4)

```bash
# Optuna로 자동 튜닝 (50회)
python scripts/optuna_tuning.py --model_type lightgbm --n_trials 50

# 결과 분석
python scripts/evaluate.py --optuna_study lightgbm_optuna
```

---

## 📚 가이드 문서 읽는 순서

1. **이 README** - 전체 구조 이해 (5분)
2. **00_AI_Engineering_Guide.md** - 5단계 프로세스 (15분)
3. **01_Model_Improvement_Strategy.md** - 5개 모델 상세 (30분)
4. **02_Experiment_Tracking.md** - 실험 추적 방법 (20분)
5. **03_Hyperparameter_Tuning.md** - 튜닝 전략 (25분)

**총 시간**: ~95분 (1.5시간)

---

## 🔧 주요 스크립트 사용법

### 기본 실험 실행
```bash
python scripts/run_experiment.py --config configs/exp_lightgbm_v1.yaml
```

### 모든 실험 비교
```bash
python scripts/evaluate.py --compare all
```

### 최고 모델 분석
```bash
python scripts/shap_analysis.py --model exp_010_lightgbm_optuna
```

### 추론 파이프라인 테스트
```bash
python scripts/inference.py --model models/production_model_v1.pkl --input data/sample.csv
```

---

## 📊 예상 성능 개선 로드맵

```
Week 1: Baseline 재현
  Ridge MAE: 0.0950
  XGBoost MAE: 0.0891

Week 2-3: 모델 개선
  LightGBM MAE: 0.0885 (+2.4% vs XGBoost)
  Segment 모델: 0.0880 (+3.1% vs XGBoost)

Week 4: 하이퍼파라미터 튜닝
  LightGBM Tuned MAE: 0.0855 (+4.0% vs XGBoost)
  ← 목표 달성! 🎉

Week 5: 최종 검증
  Test MAE: 0.0845 (+5.2% vs XGBoost) ✅
```

---

## ⚠️ 주의사항

### 중요: 시계열 데이터 특성 유지
```python
# ❌ 절대 금지
train_test_split(X, y, test_size=0.2, shuffle=True)

# ✅ 올바른 방법
split_idx = int(len(X) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]
```

### 중요: O₂ 누수 위험 관리
- O₂ (AIT_H1_902) 상관도: 0.997 → 데이터 누수 신호
- **Main 모델**: O₂ 제거 (NoLeak)
- **Proxy 모델**: O₂ 포함 (Leak) - 성능 상한선 측정용

### 중요: 과도한 튜닝 피하기
- Trial은 50~100회 정도로 충분
- 1000회 이상은 validation overfitting 위험
- Test 성능도 함께 모니터링

---

## 📖 참고 자료

| 자료 | 위치 | 용도 |
|------|------|------|
| 베이스라인 분석 | `../nox_manual_baseline/` | 데이터/피처 이해 |
| Feature Dictionary | `../nox_manual_baseline/02_feature_dictionary.md` | 피처 의미 |
| 5개 가설 | `../nox_manual_baseline/01_project_briefing.md` | 도메인 인사이트 |
| Stage 05~07 코드 | `../nox_manual_baseline/scripts/` | 구현 참고 |

---

## ❓ FAQ

**Q: 어디서 시작해야 하나?**
A: `00_AI_Engineering_Guide.md`의 Week 1 체크리스트부터!

**Q: 모델이 수렴하지 않으면?**
A: Learning rate 감소, 정규화 강화, 피처 정규화 확인

**Q: 실험이 너무 오래 걸리면?**
A: `n_estimators`를 100으로 줄여서 빠르게 확인 후 진행

**Q: 여러 모델을 동시에 돌려도 되나?**
A: 네, `n_jobs=-1`로 병렬 처리 가능 (CPU 모두 사용)

**Q: 최종 모델은 어디에 저장하나?**
A: `models/production_model_v1.pkl` + `models/production_model_v1.onnx`

---

## 📞 지원

- 📧 질문: 프로젝트 Issues 생성
- 💾 데이터: `../nox_manual_baseline/data/processed/`
- 📊 결과: `experiments/results_summary.csv`

---

**시작하기**: `/00_AI_Engineering_Guide.md`를 열어서 Week 1 시작! 🚀
