# Digital Twin 작업 가이드

## 역할
합성가스 발전소 NOx 거동을 재현하는 stateful 시뮬 엔진. Zeldovich ODE + ML 회귀 + 시간 상수 lag 모델의 하이브리드 구조.

## 포함 내용
- `simulation/engine.py` — 시뮬 루프 (sim_step)
- `simulation/chemistry.py` — Zeldovich ODE
- `simulation/lag.py` — 시간 상수 lag 모델
- `simulation/state.py` — SimulationState 도메인 객체
- `simulation/features.py` — 피처 계산
- `simulation/config.py` — τ/임계치/dt SoT (Single Source of Truth)
- `train.py`, `predict.py`, `preprocess.py` — ML 모델 학습/추론/전처리
- `models/` — 학습된 모델 아티팩트, 메타데이터
- `tests/` — pytest

기술 스택: scipy, numpy, scikit-learn, LightGBM, joblib

## ⛔ 금지 사항
- τ/임계치/dt 값을 `config.py` 외부에서 하드코딩 — SoT는 `simulation/config.py`
- 도메인 객체(SimulationState 등)를 simulation/ 외부에 정의 — SoT는 `simulation/`
- 모델 파일(`.pkl`)을 git에 커밋 — `.gitignore`로 제외됨
- Cantera 등 외부 화학 엔진 도입 — Phase 2 검토 (`[추후 결정]`)
- 시뮬 dt와 lag τ를 별도 관리 — 반드시 config 통해 일원화

## ⚠️ 학습된 주의사항
> `/learn` 명령어로 누적되는 영역.

_(아직 없음)_
