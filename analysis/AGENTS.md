# Analysis 작업 가이드

실험과 production 코드(`digital_twin/`, `apps/`)의 경계를 유지한다 — 노트북 직쓰기·raw 출력 커밋·production import가 가장 큰 노이즈 원천.

**Tradeoff**: 실험/운영을 PR 게이트로 분리하고 노트북 출력 클리어를 강제하면 즉시 production 반영과 EDA 산출물 즉시 가시성을 포기하는 대신 실험 실패의 운영 영향과 diff 노이즈·PII 노출을 차단한다.

## 1. WHAT — 이 모듈은 무엇을 하는가

EDA, 모델링 실험, 리포트 작성을 위한 실험 영역. **production 코드(`digital_twin/`, `apps/`)와 분리** 운영되며, 실험 결과는 검증 후 별도 PR로 production에 이관한다.

## 2. CONTENTS — 파일/디렉토리와 기술 스택

- `notebooks/` — Jupyter EDA 노트북 자리 (**현재 `.gitkeep`만, 비어 있음**)
- `reports/` — 분석 리포트 산출물 (markdown)
- `Engineering/configs/` — 실험 설정 (`baseline_ridge.yaml`, `exp_lightgbm_v1.yaml` 등)
- `Engineering/experiments/` — 실험 결과 (run 단위 디렉토리 + `results_summary.csv`)
- `Engineering/models/` — 실험용 모델 아티팩트
- `Engineering/scripts/` — 실험 실행 스크립트 (현재 6개):
  - `generate_synthetic_data.py` — 베이스라인 기반 synthetic 데이터 생성
  - `optuna_tuning_real.py` — Optuna 하이퍼파라미터 튜닝 (실데이터)
  - `run_all_models.py`, `run_advanced_models.py`, `run_experiment.py`, `run_with_real_data.py` — 통합/단일 실험 러너
- `Engineering/reports/` — 엔지니어링 리포트 (`00_AI_Engineering_Guide.md`부터 순서대로)
- `Engineering/HOW_TO_GUIDE.md`, `PROJECT_COMPLETION_SUMMARY.md` — 작업 안내 문서

기술 스택: Jupyter, pandas, scikit-learn, LightGBM, Optuna, matplotlib/seaborn

## 3. HOW — 일반적인 수정은 어떻게 하는가

- **새 EDA**: `notebooks/`에 노트북 추가. 데이터는 `data/raw/`에서 로드 (analysis 폴더에 raw 데이터 직접 배치 금지). 현재는 `Engineering/scripts/` 기반 스크립트 실험이 우선.
- **새 실험**: `Engineering/configs/`에 YAML 설정 → `Engineering/scripts/run_experiment.py` 또는 전용 러너로 실행 → 결과는 `Engineering/experiments/`에 run 단위 저장.
- **production 이관**: 실험 검증 완료 → `digital_twin/` 또는 `apps/`로 별도 PR로 이관. `Engineering/`에서 직접 production 코드 import 금지.
- **리포트**: `reports/` 또는 `Engineering/reports/`에 markdown으로 작성.

## 4. ⛔ HOW NOT — 시스템을 깨뜨리는 비명백한 함정

- 노트북에 raw 데이터 셀 출력 포함 커밋 — 출력 클리어 후 커밋 (PII/용량 + diff 노이즈)
- 실험 결과를 production 코드(`digital_twin/`, `apps/`)에 직접 반영 — 검증 후 별도 PR로 이관, 직쓰기 시 실험/운영 코드 경계 붕괴
- 대용량 데이터/모델을 git에 커밋 — `.gitignore` 확인 (`data/**`, `models/**` 제외), 커밋 시 repo 비대
- raw 데이터 파일을 `analysis/` 폴더에 직접 배치 — `data/raw/` 사용, 위치 분산 시 추적 어려움
- 실험 노트북/스크립트에서 production DB에 쓰기 — 읽기 전용 접근만, 쓰기 시 운영 데이터 오염
- `analysis/`에서 production 코드(`digital_twin.*`, `app.*`)를 import — 반대 방향(prod → analysis)도 금지. 경계 붕괴

## 5. WHERE — 다른 모듈과의 의존성

- **의존**:
  - `data/raw/` (git 제외 데이터셋)
  - [`database/AGENTS.md`](../database/AGENTS.md): 운영 컬럼 정의 참조 (읽기 전용)
- **피의존**: 없음 (production 코드는 analysis를 import 하지 않음). 결과는 PR 이관으로 전파.
- **경계 / 어댑터**: 실험 → production 이관은 PR 단위 (별도 디렉토리 복사 + 코드 리뷰).

## 6. WHY — 코드에 안 적힌 배경 지식

- **분리 운영 배경**: 실험 코드를 production에 섞으면 import 경로/의존성이 오염되고, 실험 실패가 운영에 영향. PR 게이트로 분리.
- **현재 노트북 디렉토리가 빈 상태**: 초기 EDA는 `Engineering/scripts/`의 스크립트 기반으로 진행되었음. 인터랙티브 EDA가 필요할 때 `notebooks/`에 추가.
- **Engineering 폴더 순서**: `00_AI_Engineering_Guide.md`부터 순서대로 읽으면 모델 개선 전략·실험 추적·하이퍼파라미터 튜닝 가이드 확보 가능.
- **PROJECT_COMPLETION_SUMMARY.md**: 프로젝트 마일스톤 누적 기록. 신규 합류자 온보딩에 유용.

## 7. COMMANDS — 빌드/테스트/린트

- 노트북 실행: Jupyter Lab 또는 VSCode
- 실험 스크립트: `python analysis/Engineering/scripts/<name>.py`
- 노트북 출력 클리어 (커밋 전): `jupyter nbconvert --clear-output --inplace notebooks/*.ipynb`

**영역 고유 명령어 가드**:
- 노트북을 출력 포함으로 커밋 — `nbconvert --clear-output` 또는 pre-commit hook으로 자동화
- `pip install` 후 `requirements.txt` 미갱신 — 다른 작업자 환경 불일치

## 8. ⚠️ LEARNED CAUTIONS — 학습된 주의사항

<!-- `learn` 스킬(`/learn` 또는 Codex의 `$learn`)로 누적되는 영역. -->

_(아직 없음)_
