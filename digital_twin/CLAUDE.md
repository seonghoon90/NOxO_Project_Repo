# Digital Twin 작업 가이드

## 역할
합성가스 발전소 NOx 거동을 재현하는 stateful 시뮬 엔진. Zeldovich ODE + ML 회귀 + 시간 상수 lag 모델의 하이브리드 구조.

## 포함 내용
- `simulation/engine.py` — 시뮬 루프 (sim_step)
- `simulation/chemistry.py` — Zeldovich ODE
- `simulation/lag.py` — 시간 상수 lag 모델
- `simulation/state.py` — SimulationState 도메인 객체 (**ControlVars 10필드 / OutputVars 5필드**)
- `simulation/features.py` — 피처 계산
- `simulation/config.py` — τ/임계치/dt SoT (Single Source of Truth, **운영 임계 9필드 포함**)
- `train.py`, `predict.py`, `preprocess.py` — ML 모델 학습/추론/전처리 (**1분 집계 + Ridge·LGB 앙상블**)
- `models/` — 학습된 모델 아티팩트 (`dt_lgb_model.pkl`, `dt_ridge_model.pkl`), 메타데이터
- `tests/` — pytest (23개 통과)

기술 스택: scipy, numpy, scikit-learn, LightGBM, joblib

## 현재 스펙 (PR #35/#37)
- **ControlVars 10개** — `state.py::ControlVars`. 단위/한계는 [추후 결정] 가안값
- **OutputVars 5개** — nox/exhaust_temp/power/lambda_/efficiency (`co` 제외, `REFACTOR_FLAME_TEMP_TO_EXHAUST_TEMP.md`)
- **모델 학습 단위 = 1분** — `preprocess.aggregate_to_1min(df)` (60행 평균)
- **앙상블 = 0.7 Ridge + 0.3 LGB** — `ENSEMBLE_W_RIDGE=0.7`, `RIDGE_ALPHA=0.01`
- **`predict()` 입력** — 최근 1초 시계열 60+ 행 (`recent_df`). 짧으면 경고 후 폴백
- **TTXM (exhaust_temp) 필수 입력** — 타겟이지만 lag 입력으로도 사용. 누락 시 ValueError
- **운영 임계 SoT** — `config.py::ThresholdConfig`. 백엔드 `GET /api/threshold`가 9필드 반환
- **신규 7개 변수 τ** — `TimeConstants` 가안 1.0초 ([조사 필요])

## ⛔ 금지 사항
- τ/임계치/dt 값을 `config.py` 외부에서 하드코딩 — SoT는 `simulation/config.py`
- 도메인 객체(SimulationState 등)를 simulation/ 외부에 정의 — SoT는 `simulation/`
- 모델 파일(`.pkl`)을 git에 커밋 — `.gitignore`로 제외됨
- Cantera 등 외부 화학 엔진 도입 — Phase 2 검토 (`[추후 결정]`)
- 시뮬 dt와 lag τ를 별도 관리 — 반드시 config 통해 일원화
- ControlVars 필드를 10개 외로 변경 — 백엔드 `app/domain/tags.py::_FIELD_RULES`와 동시 갱신 필수
- OutputVars에 `co` 부활 — 학습 타겟에서 영구 제외
- 1초 데이터로 모델 재학습 — 분포 이동·자기상관(0.989) 문제로 R² 급락 (NOx R² 0.47 ← 1분 앙상블 0.71)
- Ridge·LGB 중 하나만 단독 운영 — 외삽 능력 + 비선형 미세조정 결합이 핵심

## ⚠️ 학습된 주의사항
> `/learn` 명령어로 누적되는 영역.

_(아직 없음)_
