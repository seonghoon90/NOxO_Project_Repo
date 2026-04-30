# NOx 예측 AI 엔지니어링 가이드

> **목적**: Baseline 분석 결과를 바탕으로 AI 모델을 개선하고 프로덕션화하기 위한 실전 가이드
> **Run ID**: `nox_engineering_v1` 
> **최종 갱신**: 2026-04-30
> **현재 상태**: Engineering Phase 시작

---

## 📊 빠른 요약: 베이스라인 분석 결과

### 과거 분석 (nox_manual_baseline/)
- **Run ID**: `nox_manual_review_20260429_01`
- **완료 단계**: Stage 00P ~ 07 (모두 완료)
- **성능 Baseline**: Ridge NoLeak (성능 지표)
- **구조 Baseline**: XGBoost NoLeak (가설 검증)
- **체크포인트**: D05, D07 모두 `accepted`

### 핵심 발견 (⚠️ AI 엔지니어가 반드시 알아야 할 것)

| 위험 | 내용 | AI 엔지니어링 영향 |
|------|------|---------|
| **HYP-1: O₂ 누수** | SCR 입구 O₂ ↔ NOx 상관 0.997 | O₂를 제거한 모델을 main 모델로, O₂ 포함은 검증용만 사용 |
| **HYP-2: 부하 구간 효과** | DWATT별 NOx 생성 양상 변화 | Segment 모델(저/중/고부하) vs Global 모델 비교 필수 |
| **HYP-3: N₂ 역인과** | NQJ가 선행 지표일 수 있음 | Future NQJ 제거, 과거 NQJ만 사용 |

### 데이터 특성
- **시계열 데이터**: 1초 간격, 15일분 (1,296,000행)
- **타깃**: NOx 농도 (ppm), 평균 29.28 ± 0.19 (매우 좁은 범위)
- **주요 피처**: 온도, 압력, 출력(DWATT), N₂ 제어, IGV, 연료

---

## 🎯 AI 엔지니어링 5단계 (이 프로젝트)

### Phase 1️⃣: 베이스라인 재현 & 검증 (1주)
**목표**: Baseline 모델들을 현재 환경에서 재현하고 성능 확인

- [ ] Stage 05~07 코드 실행 재현
- [ ] Ridge NoLeak / XGBoost NoLeak 모델 성능 확인
- [ ] Ablation 결과 검증
- [ ] **산출물**: `reports/baseline_reproduction.md`

### Phase 2️⃣: 모델 개선 실험 (2주)
**목표**: Baseline을 넘는 더 나은 모델 찾기

#### Experiment 1: O₂ 누수 위험 관리
- O₂ 제거 모델 (NoLeak) vs O₂ 포함 모델 (Leak) 성능 비교
- O₂를 Proxy 변수로 취급할 때의 성능 상한선 측정

#### Experiment 2: 모델 아키텍처 개선
- **LightGBM** (XGBoost보다 빠름)
- **TabNet** (해석성 + 성능)
- **Neural Network** (MLP with batch norm & dropout)
- **앙상블** (Ridge + XGBoost + LightGBM)

#### Experiment 3: 부하 구간별 세분화
- Global 모델 1개 vs Segment 모델 3개 (저/중/고부하)
- Segment 모델들의 가중합산 성능 비교

#### Experiment 4: 피처 엔지니어링 고도화
- **Interaction 피처**: DWATT × 온도, DWATT × N₂ 등
- **시계열 피처**: 과거 30/60초 이동평균, 변화율
- **도메인 피처**: 압력비, 온도차, 운전 효율 지표

**산출물**: `reports/model_improvement_experiments.md`

### Phase 3️⃣: 하이퍼파라미터 튜닝 (1주)
**목표**: 최고 성능 모델의 하이퍼파라미터 최적화

- Optuna/Hyperopt를 이용한 자동 튜닝
- GridSearch vs RandomSearch vs Bayesian 비교
- **카테고리**: Learning rate, depth, lambda, dropout 등
- **제약**: 과도한 튜닝으로 인한 과적합 방지

**산출물**: `reports/hyperparameter_tuning.md`

### Phase 4️⃣: 검증 & 해석 (1주)
**목표**: 최종 모델의 신뢰성 확인 및 해석

- **Holdout 성능**: 시간순 테스트셋에서 재현성 확인
- **특성 중요도 분석**: SHAP/LIME으로 모델 결정 근거 해석
- **에러 분석**: Residual plot, 부하 구간별 에러율
- **Domain 검증**: 도메인 전문가와 함께 결과 해석

**산출물**: `reports/final_model_validation.md`

### Phase 5️⃣: 배포 & 모니터링 준비 (1주)
**목표**: 프로덕션 배포를 위한 구조화

- **모델 저장**: ONNX/PKL 형식 표준화
- **Inference 파이프라인**: 입력 전처리 → 예측 → 출력 형식 정의
- **성능 모니터링**: 시간대별 MAE/RMSE 추적
- **Drift 감지**: 데이터 분포 변화 모니터링

**산출물**: `scripts/inference_pipeline.py`, `models/final_model.pkl`

---

## 🔧 AI 엔지니어의 일상 업무 흐름

### Daily Workflow

```
1️⃣ 오전: 어제 실험 결과 검토
   - 자동으로 저장된 experiments/*.json 검토
   - 성능 개선된 모델 발견 시 추가 검증

2️⃣ 오전: 오늘 실험 계획
   - 어제 배운 인사이트 → 오늘 실험 설계
   - Experiment tracker 업데이트

3️⃣ 오후: 실험 실행 (자동화 스크립트)
   - python scripts/run_experiment.py --config configs/exp_lightgbm.yaml
   - 결과는 자동 저장, 로그 자동 기록

4️⃣ 저녁: 해석 & 문서화
   - 결과 분석, SHAP plot 생성
   - 결론을 reports/에 추가
   - Git commit with experiment metadata
```

### 실험 추적 (Experiment Tracking)
모든 실험은 다음과 같이 기록됨:

```json
{
  "experiment_id": "exp_001_lightgbm_v1",
  "date": "2026-04-30",
  "model_type": "LightGBM",
  "config": "configs/exp_lightgbm.yaml",
  "train_mae": 0.087,
  "val_mae": 0.092,
  "test_mae": 0.101,
  "features_used": 88,
  "notes": "Added interaction features DWATT×TTXM"
}
```

---

## 📁 프로젝트 폴더 구조 설명

```
analysis/Engineering/
├── 00_AI_Engineering_Guide.md          ← 이 파일
├── 01_Model_Improvement_Strategy.md    (각 모델별 상세 전략)
├── 02_Experiment_Tracking.md           (실험 추적 방법)
├── 03_Hyperparameter_Tuning.md         (튜닝 가이드)
│
├── configs/                            (설정 파일)
│   ├── baseline_ridge.yaml
│   ├── baseline_xgboost.yaml
│   ├── exp_lightgbm_v1.yaml
│   ├── exp_tabnet_v1.yaml
│   └── exp_neural_network_v1.yaml
│
├── scripts/                            (실행 스크립트)
│   ├── run_experiment.py               (통합 실험 실행)
│   ├── preprocess.py                   (데이터 전처리)
│   ├── train_model.py                  (모델 학습)
│   ├── evaluate.py                     (평가 및 분석)
│   └── inference.py                    (추론 파이프라인)
│
├── experiments/                        (실험 결과)
│   ├── metadata/
│   │   ├── exp_001_ridge_baseline.json
│   │   ├── exp_002_xgboost_baseline.json
│   │   └── exp_003_lightgbm_v1.json
│   └── models/
│       ├── exp_001_model.pkl
│       ├── exp_002_model.pkl
│       └── exp_003_model.pkl
│
├── models/                             (최종 모델)
│   ├── production_model_v1.pkl
│   ├── production_model_v1.onnx        (배포용)
│   └── model_metadata.json
│
└── reports/                            (분석 보고서)
    ├── baseline_reproduction.md
    ├── model_improvement_experiments.md
    ├── hyperparameter_tuning.md
    ├── final_model_validation.md
    └── figures/
        ├── shap_importance.png
        ├── residual_analysis.png
        └── performance_comparison.png
```

---

## ✅ 체크리스트: AI 엔지니어가 해야 할 일

### Week 1: 베이스라인 재현
- [ ] `../nox_manual_baseline/scripts/` 코드 분석
- [ ] Stage 05~07 스크립트 실행
- [ ] Ridge/XGBoost 성능 수치 기록
- [ ] 로컬 환경에서 재현 가능 여부 확인

### Week 2-3: 모델 개선 실험
- [ ] LightGBM 모델 학습 (configs/exp_lightgbm_v1.yaml)
- [ ] TabNet 모델 학습
- [ ] Segment 모델 (저/중/고부하) 학습
- [ ] 앙상블 모델 학습
- [ ] 4개 모델 성능 비교 표 작성

### Week 4: 하이퍼파라미터 튜닝
- [ ] Optuna로 최고 모델 튜닝
- [ ] 튜닝 전/후 성능 비교
- [ ] 과적합 여부 확인

### Week 5: 최종 검증 & 배포 준비
- [ ] SHAP 해석성 분석
- [ ] Residual 분석으로 에러 패턴 파악
- [ ] 모델 저장 (pkl, onnx)
- [ ] 추론 파이프라인 코드 작성

---

## 🚀 시작 명령어

### 1단계: 베이스라인 재현
```bash
cd analysis/Engineering
python scripts/run_experiment.py --mode baseline_reproduction
```

### 2단계: 새 모델 실험
```bash
python scripts/run_experiment.py --config configs/exp_lightgbm_v1.yaml
```

### 3단계: 실험 결과 비교
```bash
python scripts/evaluate.py --compare exp_001 exp_002 exp_003
```

---

## 📚 참고 자료

- **Baseline 분석**: `../nox_manual_baseline/00_full_pipeline_baseline.md`
- **Feature Dictionary**: `../nox_manual_baseline/02_feature_dictionary.md`
- **5개 가설**: `../nox_manual_baseline/01_project_briefing.md`
- **Stage 05~07 코드**: `../nox_manual_baseline/scripts/stage05_to_07_baseline.py`

---

## 🎓 핵심 학습 포인트

1. **시계열 데이터 다루기**: Temporal holdout이 왜 중요한가?
2. **Domain Knowledge**: NOx 예측은 센서 보정/누수 이해가 필수
3. **해석 가능성**: 블랙박스 모델보다 도메인 검증 가능한 모델이 낫다
4. **실험 추적**: 작은 개선도 기록하면 나중에 복합 효과 발견 가능
5. **배포 관점**: 높은 성능보다 안정적인 성능이 프로덕션에서는 더 중요

---

## ❓ 자주 묻는 질문 (FAQ)

**Q: O₂를 꼭 제거해야 하나?**
A: 네. 0.997 상관은 데이터 누수 신호입니다. Main 모델은 O₂ 제거, Proxy 모델로 O₂ 포함 모델을 따로 관리하세요.

**Q: Ridge가 XGBoost보다 성능이 낮은데 왜 사용하나?**
A: Ridge는 성능 baseline, XGBoost는 구조 baseline입니다. Ridge의 단순함이 해석 가능성에서 장점이고, 새 모델들은 이 둘을 모두 넘어야 의미가 있습니다.

**Q: 실험이 너무 많으면 어떻게 하나?**
A: `experiments/metadata/` 폴더에 자동 저장되는 JSON으로 빠르게 스캔할 수 있습니다. Excel로 export해서 성능 비교표를 만들면 됩니다.

**Q: 모델을 언제 저장해야 하나?**
A: 모든 실험은 `experiments/models/`에, 최종 선택 모델만 `models/production_model_v1.pkl`로 저장하세요.

---

**다음 문서**: `01_Model_Improvement_Strategy.md` (각 모델별 상세 설명)
