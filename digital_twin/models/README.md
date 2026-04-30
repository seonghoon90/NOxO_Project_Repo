# Digital Twin Models — 인도 규약

[가이드 §9 — "우선 생성할 대상" 중 모델 메타 파일 영역]

이 폴더는 **모델링 담당자 → DT 담당자**로 학습된 회귀 모델을 인도하는 단일 진입점이다.
백엔드의 `MLPredictor`(`apps/backend/app/adapters/predictor/ml.py`)는 본 폴더의
산출물만 바라보도록 구성된다.

---

## 1. 인도 대상 파일

[가이드 §5 단계 4 — 정상상태 ML 회귀 모델 산출물]

| 파일명 | 역할 | 학습 타깃 | 단위 |
|--------|------|---------|------|
| `steady_state_model.pkl` | 정상상태 멀티 타겟 회귀 | nox_ppm, exhaust_temp, power | ppm / °C / MW |
| `metadata.json`          | 모델 버전/입력 피처 명세 | - | - |

> 타겟 3개(nox_ppm, exhaust_temp, power)를 단일 멀티 타겟 모델로 학습한다.
> - `exhaust_temp`: 화염온도 직접 측정 불가 → IGCC.CC.G1.TTXM(배기온도)으로 대체
> - `co`, `efficiency`: features.py 수식으로 계산하므로 ML 타겟 제외
> 누락 시 `StubPredictor` 또는 `features.py` 근사식이 임시 대체한다.

---

## 2. 입력 피처 계약

[가이드 단계 0 — 변수 사전 / `apps/backend/app/domain/tags.py`와 일치]

모든 모델은 **동일한 입력 피처 순서**로 학습되어야 한다:

```python
# digital_twin.simulation.state.ControlVars 정의 순서와 동일
features = [
    "syngas_flow",   # IGCC.CC.G1.ca_fqsg_cl
    "n2_offset",     # IGCC.CC.G1.NQKR3_MONITOR
    "igv_opening",   # IGCC.CC.G1.csgv
]
```

추가 파생 피처가 필요할 경우 `digital_twin.simulation.features` 모듈의 함수를
**학습 시점과 추론 시점 모두에서 동일하게** 호출해야 한다 (가이드 단계 2 원칙).

---

## 3. 직렬화 규약

```python
import joblib

# 저장
joblib.dump(model, "digital_twin/models/nox_steady_model.pkl")

# 로드 (백엔드 MLPredictor에서 자동 수행)
model = joblib.load("digital_twin/models/nox_steady_model.pkl")
```

- 직렬화 도구: **joblib** (가이드 §단계 4 도구 명세)
- 모델 파이프라인은 sklearn `Pipeline` 형태로 묶어 전처리(스케일러 등)까지 포함시킬 것.
  → 추론 측에서 별도 전처리 코드를 두지 않기 위함.

---

## 4. metadata.json 스키마

```json
{
  "version": "v1.0.0",
  "trained_at": "2026-04-30T11:12:35Z",
  "framework": "xgboost",
  "framework_version": "2.0.3",
  "feature_order": ["syngas_flow", "n2_offset", "igv_opening"],
  "targets": ["nox_ppm", "exhaust_temp", "power"],
  "target_units": ["ppm", "°C", "MW"],
  "metrics": {
    "test_mae": 0.0102,
    "test_rmse": 0.0186
  },
  "data_source": "real_data",
  "notes": "exp_017 결과를 직렬화한 것"
}
```

> `analysis/Engineering/experiments/metadata/exp_017_xgboost_realdata.json`의
> 메타데이터 구조를 본 스키마로 변환해 함께 저장.

---

## 5. 버전 관리

- 파일명에 버전을 박지 않는다. 대신 `metadata.json`의 `version` 필드를 진실원으로 본다.
- 과거 버전이 필요할 경우: `models/archive/v0_9_0/` 형태의 하위 폴더로 이동.
- 백엔드는 항상 본 폴더의 최신 버전 1개만 로드.

---

## 6. 백엔드 연결 흐름

```
┌────────────────────┐    joblib.load    ┌──────────────────────┐
│ digital_twin/      │ ─────────────────▶│ MLPredictor          │
│   models/*.pkl     │                   │ (adapters/predictor) │
└────────────────────┘                   └──────────┬───────────┘
                                                    │ predict(ControlVars)
                                                    ▼
                                         ┌──────────────────────┐
                                         │ digital_twin/        │
                                         │   simulation/        │
                                         │   engine.sim_step    │
                                         └──────────────────────┘
```

---

## 7. 오픈 이슈 (가이드 §10)

- [ ] 입력 피처 최종 목록 — `[DB 협의 필요]`
- [ ] 학습 데이터 정상상태 구간 정의 기준 — 단계 1 완료 후
- [ ] LSTM 등 동적 ML 도입 여부 — `[추후 결정]`
- [ ] 모델 재학습 트리거(drift 감지) — Phase 2
