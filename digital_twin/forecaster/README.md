# Forecaster — 5분 뒤 NOx 예측 모델 패키지

기존 시뮬레이션 모델(`digital_twin/simulation/`, `digital_twin/predict.py`)과 **완전히 독립된**
5분 horizon NOx 예측 모듈. 학습된 LightGBM + Ridge 앙상블 모델을 통해
1초 단위 시계열에서 5분 뒤 NOx 값을 단발 예측한다.

## 패키지 구성

```
digital_twin/forecaster/
├── __init__.py           # 공개 API: load_model, predict
├── preprocess.py         # 피처 엔지니어링 + 타깃 생성
├── train.py              # 학습 스크립트 (CLI 진입점)
├── predict.py            # 추론 인터페이스
├── cli.py                # 사용자용 CLI (info / predict / evaluate)
├── ensemble.py           # Ridge+LGB 앙상블 컨테이너 (pickle 호환용)
├── models/
│   ├── forecaster_lgb_model.pkl     # 학습된 모델 (이 패키지에 동봉)
│   └── forecaster_metadata.json     # 학습 메타데이터
└── tests/                # pytest (9개)
```

## 빠른 사용

### 1. 모델 정보 확인

```bash
python -m digital_twin.forecaster.cli info
```

### 2. 새 데이터로 5분 뒤 NOx 예측 (단일 호출)

```bash
python -m digital_twin.forecaster.cli predict --data path/to/recent.csv
```

출력 예시:
```json
{
  "predicted_nox_5min_later": 29.187,
  "current_nox": 29.142,
  "delta": 0.045,
  "input_rows": 900
}
```

### 3. 전체 CSV로 평가

```bash
python -m digital_twin.forecaster.cli evaluate \
    --data path/to/test.csv \
    --output results.csv
```

### 4. Python API 직접 사용

```python
import pandas as pd
from digital_twin.forecaster import load_model, predict

# 모델 로드 (1회)
loaded = load_model()

# 추론 (매 시점)
recent_df = pd.read_csv("recent_15min.csv")  # 1초 raw, 최소 15분(900행)
predicted_nox = predict(loaded, recent_df=recent_df)
print(f"5분 뒤 NOx: {predicted_nox:.3f} ppm")
```

## 모델 재학습

```bash
python -m digital_twin.forecaster.train \
    --data path/to/train.csv \
    --output digital_twin/forecaster/models/ \
    --n-estimators 500 \
    --learning-rate 0.03 \
    --max-depth 8 \
    --subsample-sec 5 \
    --ensemble-w-ridge 0.80
```

## 입력 데이터 요구사항

- **형식**: 1초 raw CSV (header=0, skiprows=[1,2,3,4] — IGCC DGAN 표준 포맷)
- **필수 컬럼**: `digital_twin.preprocess.RAW_FEATURES` 39개 + `IGCC.CC.G1.TTXM` + `IGCC.DeNOX.AT_H1_901_PV` (NOx) + `IGCC.CC.G1.DWATT` + `IGCC.DeNOX.AIT_H1_902` (선택)
- **추론 시 길이**: 최소 900행(15분) 권장 — lag/rolling warmup
- **누락 컬럼**: 모델은 graceful degrade (특히 O2는 0 폴백 + warning)

## 백엔드 통합

`apps/backend/app/adapters/forecaster/ml.py::MLForecaster`가 본 패키지를 위임 호출한다.

```bash
# 백엔드에서 ML forecaster 활성화
export USE_ML_FORECASTER=1
uvicorn app.main:app
```

`POST /api/prediction` 호출 시 자동으로 본 모델이 사용된다.

## 성능 지표

마지막 검증 holdout (`NOx_test_20250825.csv`, 85,351개 1초 샘플):

| 지표 | 값 |
|------|---:|
| **R²** | **0.677** |
| MAE | 0.062 ppm |
| RMSE | 0.081 ppm |
| Persistence 대비 R² | +0.21 |

### 모델 진화 (참고)

| 버전 | 핵심 변경 | R² |
|---|---|---:|
| v1 | 1분 집계, LGB 단일 | 0.084 (망함) |
| v2 | 1초 단위 + NOx lag | 0.522 |
| v2.2 | Ridge+LGB 앙상블 | 0.592 |
| v2.5 | 일반화 피처 105개 | 0.657 |
| v2.6 | O2 제외 (보수적) | 0.625 |
| **v2.7 ← 현재** | **O2 포함 (5분 horizon 정당)** | **0.677** |

## 데이터의 본질적 한계

- 정상상태 운전 데이터(NOx std ≈ 0.14 ppm)에서 점 예측 R² 이론 천장: **~0.63**
- 현재 v2.7은 천장 부근 도달
- R²=0.9+ 도달은 NOx 변동성 큰 데이터(부하 변동/시동·정지) 필요

## 디자인 결정 (요약)

| 항목 | 선택 | 근거 |
|---|---|---|
| 시간 단위 | 1초 raw | 1분 집계는 noise 평균화로 NOx 미세 변동 소실 → 점 예측 망함 |
| Target | shift(-300) 점 예측 | 원래 요구 "5분 뒤 NOx" 충실 (평균 예측은 task 변경이라 reject) |
| 모델 | Ridge α=1.0 + LGB(n_est=500) 앙상블 (w_ridge=0.8) | Ridge가 외삽 강건, LGB는 비선형 보완 |
| 피처 | 213개 (RAW + NOx lag/diff/roll + 운전 변수 diff/roll/lag + 상호작용 + 시간 + O2) | Forecast01 feature importance 참고 |
| 누수 방지 | NQJO2/O2 직접 센서 포함 (5분 horizon이라 정당) | t+5min 예측에서 O2(t)는 미래 정보 아님 |

## 테스트

```bash
pytest digital_twin/forecaster/tests/ -v
```

9개 테스트 모두 통과.

## 관련 문서

- 설계: `docs/superpowers/specs/2026-05-12-forecaster-5min-nox-design.md` (로컬)
- 구현 계획: `docs/superpowers/plans/2026-05-12-forecaster-5min-nox.md` (로컬)
- 참조 모델: `docs/Share/16_forecast01_no_o2_model_only_brief.md`
